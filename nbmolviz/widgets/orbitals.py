# Copyright 2017 Autodesk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections

import ipywidgets as ipy

from ..viewers import GeometryViewer
from ..widget_utils import process_widget_kwargs
from .selector import SelectionGroup, Selector, create_value_selector


class OrbitalViewer(SelectionGroup):
    """
    Subclass of the standard geometry viewer with added UI for rendering orbitals

    Args:
        mol (mdt.Molecule): a molecule with A) orbitals, and
                            B) an energy model with calculate_orbital_grid
        **kwargs (dict): kwargs for the viewer
    """
    def __init__(self, mol, **kwargs):
        self.viewer = GeometryViewer(mol=mol, **process_widget_kwargs(kwargs))
        self.viewer.wfns = [mol.wfn]
        self.uipane = OrbitalUIPane(self, hostheight=self.viewer.layout.height)
        hb = ipy.HBox([self.viewer, self.uipane])
        super(OrbitalViewer, self).__init__([hb])


class OrbitalUIPane(Selector, ipy.Box):
    # TODO: deal with orbitals not present in all frames of a trajectory
    # TODO: deal with orbital properties (occupation and energy) changing over a trajectory
    def __init__(self, viz, hostheight, **kwargs):
        self.viz = viz
        kwargs.setdefault('width', '325px')

        self.type_dropdown = ipy.Dropdown(options=self.viz.viewer.wfn.orbitals.keys())
        initial_orb = 'canonical'
        if initial_orb not in self.type_dropdown.options:
            initial_orb = self.type_dropdown.options.iterkeys().next()
        self.type_dropdown.value = initial_orb
        self.type_dropdown.observe(self.new_orb_type, 'value')

        kwargs['height'] = str(int(hostheight.rstrip('px')) - 50) + 'px'
        height = str(int(hostheight.rstrip('px')) - 125) + 'px'

        self.orblist = ipy.Dropdown(options={None: None},
                                    layout=ipy.Layout(
                                            width=kwargs['width'],
                                            height=height))

        self.isoval_selector = create_value_selector(ipy.FloatSlider,
                                                     value_selects='orbital_isovalue',
                                                     min=0.0, max=0.075,
                                                     value=0.01, step=0.00075,
                                                     description='Isovalue',
                                                     readout_format='.4f',
                                                     layout=ipy.Layout(width=kwargs['width']))

        self.orb_resolution = ipy.Text(description='Orbital resolution',
                                       layout=ipy.Layout(width='75px'))
        self.orb_resolution.value = '40'  # string because it's required for the 'on_submit' method
        self.change_resolution()
        self.orb_resolution.on_submit(self.change_resolution)

        children = [self.type_dropdown, self.orblist, self.isoval_selector, self.orb_resolution]
        super(OrbitalUIPane, self).__init__(children, **process_widget_kwargs(kwargs))
        self.new_orb_type()
        self.orblist.observe(self.new_orbital_selection, 'value')

    def new_orbital_selection(self, *args):
        self.fire_selection_event({'orbname': (self.type_dropdown.value, self.orblist.value)})

    def handle_selection_event(self, *args):
        # TODO: update the selected orbitals if something actually else triggers this
        pass

    def new_orb_type(self, *args):
        """Create list of available orbitals when user selects a new type
        """
        wfn = self.viz.viewer.wfn
        newtype = self.type_dropdown.value
        neworbs = wfn.orbitals[newtype]
        orblist = collections.OrderedDict()

        orblist[None] = None
        for i, orb in enumerate(neworbs):
            if hasattr(orb, 'unicode_name'):
                orbname = orb.unicode_name
            else:
                orbname = orb.name

            meta = ''
            if orb.energy is not None:
                meta = '{:.02fP}'.format(orb.energy.defunits())
            if orb.occupation is not None:
                if meta: meta += ', '
                meta += 'occ %.2f' % orb.occupation
            if meta:
                desc = '%d. %s   (%s)' % (i, orbname, meta)
            else:
                desc = '%d. %s' % (i, orbname)
            orblist[desc] = i
        self.orblist.value = None
        self.orblist.options = orblist

    def change_resolution(self, *args):
        viewer = self.viz.viewer
        viewer.orbital_spec['npts'] = int(self.orb_resolution.value)
        if viewer.current_orbital is not None:
            viewer.draw_orbital(viewer.current_orbital, **viewer.orbital_spec)


