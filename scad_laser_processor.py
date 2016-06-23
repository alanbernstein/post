#!/usr/bin/python
"""process a scad file to be opened in corel, for use on ULS laser cutter
usage:
laser file.scad  # export to svg, then add mm units and reduce stroke width
laser file.svg   # modify existing svg file
laser *.scad     # process batch
laser            # process most recently updated .scad file"""

import sys
import os
import subprocess
import re
import glob


from panda.debug import debug, jprint

# TODO: automatically export all layers, recombine into single SVG

class ScadLaserFileProcessor(object):
    default_unit = 'mm'
    default_stroke_width = .1
    scad_cmd = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

    def __init__(self, fname):
        """init with either
        file.scad (export to svg first) or
        file.svg (just add units)"""
        pth, filename = os.path.split(fname)
        basename, ext = os.path.splitext(filename)
        #debug()
        if ext == '.scad':
            self.scadfile = fname
            self.svgfile = pth + basename + '.svg'
            print('scad file: %s' % self.scadfile)
        elif ext == '.svg':
            self.scadfile = None
            self.svgfile = fname
            print('svg file: %s' % self.svgfile)

    def run(self):
        if self.scadfile:
            print('  exporting: %s' % self.svgfile)
            self.export_scad_to_svg()

            # TODO: detect current layer, and reset to that when done
            self.detect_scad_layers()
            # self.export_all_layers_to_svg()

        print('  changing units and width: %s' % self.svgfile)
        fix_svg_file_for_laser(self.svgfile, self.default_unit, self.default_stroke_width)
        # for layername in self.layers:
        #   fix_svg_file_for_laser(svgfile + suffix)

        # self.combine_svg_layers()

    def export_scad_to_svg(self, suffix=None):
        suffix = suffix or ''
        # TODO: add suffix
        cmd = '%s -o %s %s' % (self.scad_cmd, self.svgfile, self.scadfile)
        res = subprocess.check_output(cmd, shell=True)

    def detect_scad_layers(self):
        # layers=["cut", "etch"];
        with open(self.scadfile, 'r') as f:
            lines = f.readlines()

        for line in lines:
            line = line.replace(' ', '')
            if re.match('^layers=\[', line):
                break

        match = re.search('\[([a-z ",]*)\];', line)
        layer_str = match.group()[1:-2]
        self.layer_names = layer_str.split(',')
        self.layer_names = [l[1:-1] for l in self.layer_names]

        print('found %d layers in scad file: %s' % (len(self.layer_names), self.layer_names))

    def set_layer_mode(self, layername):
        with open(self.scadfile, 'r') as f:
            lines = f.readlines()

        with open(self.scadfile, 'w') as f:
            for line in lines:
                line = re.sub('^MODE="([a-z])*";', 'MODE="%s";', layername)
                f.write(line)


    def export_all_layers_to_svg(self):
        for name in self.layer_names:
            self.set_layer_mode(name)
            self.export_scad_to_svg(suffix=name)

    def combine_svg_layers(self):
        pass


def fix_svg_file_for_laser(svgfile, unit, width):
    """add units to svg file, change stroke-width"""
    # default stroke width is .5 - this causes "no data in document" error
    # ideally, need a hairline width, but this is a corel concept, not explicitly available in svg.
    # width=.387 -> fail
    # width=.384 -> success
    # the boundary is just about .004", for whatever reason...
    # just use 0.1

    with open(svgfile, 'r') as f:
        lines = f.readlines()

    with open(svgfile, 'w') as f:
        for line in lines:
            line = re.sub('width="([0-9]*)"', 'width="\\1%s"' % unit, line)
            line = re.sub('height="([0-9]*)"', 'height="\\1%s"' % unit, line)
            line = re.sub('stroke-width="0.5"', 'stroke-width="%0.1f"' % width, line)
            f.write(line)
            #print(line)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('processing most recently modified .scad file')
        scad_fnames = glob.glob('*.scad')
        scad_fnames.sort(key=lambda x: os.stat(x).st_mtime)
        fnames = scad_fnames[-1:]

    elif sys.argv[1] in ['h', 'help']:
        print(__doc__)
        exit(0)

    else:
        fnames = sys.argv[1:]

    for fname in fnames:
        # TODO: autodetect extension - kind of useless with the 'most recent' functionality working
        print(fname)
        processor = ScadLaserFileProcessor(fname)
        processor.run()
