# Copyright (c) 2004-2008 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""diagram objects
"""

from logilab import astng
from pyreverse.utils import is_interface

def set_counter(value):
    Figure._UID_COUNT = value
    
class Figure:
    _UID_COUNT = 0
    def __init__(self):
        Figure._UID_COUNT += 1
        self.fig_id = Figure._UID_COUNT
        
class Relationship(Figure):
    """a relation ship from an object in the diagram to another
    """
    def __init__(self, from_object, to_object, relation_type, name=None):
        Figure.__init__(self)
        self.from_object = from_object
        self.to_object = to_object
        self.type = relation_type
        self.name = name
        
    
class DiagramEntity(Figure):
    """a diagram object, ie a label associated to an astng node
    """
    def __init__(self, title='No name', node=None):
        Figure.__init__(self)
        self.title = title
        self.node = node

class ClassDiagram(Figure):
    """a class diagram objet
    """
    TYPE = 'class'
    def __init__(self, title='No name'):
        Figure.__init__(self)
        self.title = title
        self.objects = []
        self.relationships = {}
        self._nodes = {}
        
    def add_relationship(self, from_object, to_object, relation_type, name=None):
        """create a relation ship
        """
        rel = Relationship(from_object, to_object, relation_type, name)
        self.relationships.setdefault(relation_type, []).append(rel)

    def get_relationship(self, from_object, relation_type):
        """return a relation ship or None
        """
        for rel in self.relationships.get(relation_type, ()):
            if rel.from_object is from_object:
                return rel
        raise KeyError(relation_type)
    
    def add_object(self, title, node, show_attr = None):
        """create a diagram object
        """
        assert not self._nodes.has_key(node)
        ent = DiagramEntity(title, node)
        if isinstance(node, astng.Class) and show_attr:
            ent.methods = [m for m in node.values()
                       if isinstance(m, astng.Function) and show_attr(m.name)]
            ent.attrs = [name for (name,v) in node.instance_attrs_type.items()
                         if show_attr(name)]
        self._nodes[node] = ent
        self.objects.append(ent)

    def nodes(self):
        """return the list of underlying nodes
        """
        return self._nodes.keys()

    def has_node(self, node):
        """return true if the given node is included in the diagram
        """
        return self._nodes.has_key(node)
        
    def object_from_node(self, node):
        """return the diagram object mapped to node
        """
        return self._nodes[node]
            
    def classes(self):
        """return all class nodes in the diagram"""
        return [o for o in self.objects if isinstance(o.node, astng.Class)]

    def classe(self, name):
        """return a klass by its name, raise KeyError if not found
        """
        for klass in self.classes():
            if klass.node.name == name:
                return klass
        raise KeyError(name)
    
    def extract_relationships(self):
        """extract relation ships between nodes in the diagram
        """
        for obj in self.classes():
            node = obj.node
            # shape
            if is_interface(node):
                obj.shape = 'interface'
            else:
                obj.shape = 'class'
            # inheritance link
            for par_node in node.ancestors(recurs=False):
                try:
                    par_obj = self.object_from_node(par_node)
                    self.add_relationship(obj, par_obj, 'specialization')
                except KeyError:
                    continue
            # implements link
            for impl_node in node.implements:
                try:
                    impl_obj = self.object_from_node(impl_node)
                    self.add_relationship(obj, impl_obj, 'implements')
                except KeyError:
                    continue
            # associations link
            for name, values in node.instance_attrs_type.items():
                for value in values:
                    if value is astng.YES:
                        continue
                    if isinstance( value, astng.Instance):
                        value = value._proxied
                    try:
                        ass_obj = self.object_from_node(value)
                        self.add_relationship(obj, ass_obj, 'association', name)
                    except KeyError:
                        continue
        
class PackageDiagram(ClassDiagram):
    TYPE = 'package'
    
    def modules(self):
        """return all module nodes in the diagram"""
        return [o for o in self.objects if isinstance(o.node, astng.Module)]

    def module(self, name):
        """return a module by its name, raise KeyError if not found
        """
        for mod in self.modules():
            if mod.node.name == name:
                return mod
        raise KeyError(name)
    
    def extract_relationships(self):
        """extract relation ships between nodes in the diagram
        """
        ClassDiagram.extract_relationships(self)
        for obj in self.classes():
            node = obj.node
            # ownership
            try:
                mod = self.object_from_node(node.root())
                self.add_relationship(obj, mod, 'ownership')
            except KeyError:
                continue
        for obj in self.modules():
            obj.shape = 'package'
            # dependancies
            for dep in obj.node.depends:
                try:
                    dep = self.module(dep)
                except KeyError:
                    continue
                self.add_relationship(obj, dep, 'depends')