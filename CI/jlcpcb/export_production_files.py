"""Headless driver for Bouni's kicad-jlcpcb-tools plugin.

The plugin has no command-line mode, so this script loads the board with
KiCad's pcbnew Python module and runs the plugin's own Store, Library and
Fabrication classes in the same order as the plugin's "Generate" button
(mainwindow.generate_fabrication_data). All output logic stays in the plugin;
this file only replaces the GUI window that normally owns those objects.

Usage:
    python3 export_production_files.py <plugin_dir> <board.kicad_pcb>

<plugin_dir> must be a checkout of the plugin with settings.json and
jlcpcb/corrections.db already copied in (the workflow does this).
"""

import importlib
import json
import logging
import os
import sys
import types

PACKAGE = "jlcpcb_tools"


class _ErrorCounter(logging.Handler):
    """Count ERROR records so a failed plot fails the job instead of being ignored."""

    def __init__(self):
        super().__init__(logging.ERROR)
        self.count = 0

    def emit(self, record):
        self.count += 1


def _ensure_wx():
    """Use the real wxPython if KiCad ships it, otherwise a minimal stand-in.

    helpers.py, library.py and events.py import wx at module level (events.py
    also calls wx.lib.newevent.NewEvent()), but nothing on the export path uses it.
    """
    try:
        import wx.lib.newevent  # noqa: F401  pylint: disable=import-error,import-outside-toplevel,unused-import
        import wx.dataview  # noqa: F401  pylint: disable=import-error,import-outside-toplevel,unused-import
    except ImportError:
        logging.getLogger(__name__).info("wxPython not available, using a stub (GUI only)")
        wx = types.ModuleType("wx")
        wx.dataview = types.ModuleType("wx.dataview")
        wx.lib = types.ModuleType("wx.lib")
        wx.lib.newevent = types.ModuleType("wx.lib.newevent")
        wx.lib.newevent.NewEvent = lambda: (type("Event", (), {}), object())
        sys.modules.update(
            {
                "wx": wx,
                "wx.dataview": wx.dataview,
                "wx.lib": wx.lib,
                "wx.lib.newevent": wx.lib.newevent,
            }
        )


def _ensure_requests():
    """library.py imports requests only to download the parts database."""
    try:
        import requests  # noqa: F401  pylint: disable=import-error,import-outside-toplevel,unused-import
    except ImportError:
        logging.getLogger(__name__).info("requests not available, using a stub (downloads only)")
        sys.modules["requests"] = types.ModuleType("requests")


def _load_plugin(plugin_dir):
    """Import the plugin's modules without running its __init__.py (which registers the GUI action)."""
    lib_path = os.path.join(plugin_dir, "lib")
    if lib_path not in sys.path:
        sys.path.append(lib_path)
    package = types.ModuleType(PACKAGE)
    package.__path__ = [plugin_dir]
    sys.modules[PACKAGE] = package
    _ensure_wx()
    _ensure_requests()
    return (
        importlib.import_module(f"{PACKAGE}.store").Store,
        importlib.import_module(f"{PACKAGE}.library").Library,
        importlib.import_module(f"{PACKAGE}.fabrication").Fabrication,
        importlib.import_module(f"{PACKAGE}.helpers").PLUGIN_PATH,
    )


class HeadlessJLCPCBTools:
    """Stands in for the plugin's main window (JLCPCBTools) as the parent object."""

    def __init__(self, plugin_dir, board):
        Store, Library, Fabrication, plugin_path = _load_plugin(plugin_dir)
        self.logger = logging.getLogger(__name__)
        self.board = board
        # Same as JLCPCBTools.__init__
        self.project_path = os.path.split(board.GetFileName())[0]
        self.board_name = os.path.split(board.GetFileName())[1]
        # Same as JLCPCBTools.load_settings
        with open(os.path.join(plugin_path, "settings.json"), encoding="utf-8") as j:
            self.settings = json.load(j)
        # Same order as JLCPCBTools: init_library, init_store, init_fabrication
        self.library = Library(self)
        self.store = Store(self, self.project_path, board)
        self.fabrication = Fabrication(self, board)

    def count_order_number_placeholders(self):
        """Mirror of JLCPCBTools.count_order_number_placeholders."""
        import pcbnew  # pylint: disable=import-error,import-outside-toplevel

        count = 0
        for drawing in self.board.GetDrawings():
            if drawing.IsOnLayer(pcbnew.F_SilkS) or drawing.IsOnLayer(pcbnew.B_SilkS):
                if isinstance(drawing, pcbnew.PCB_TEXT):
                    if drawing.GetText().strip() == "JLCJLCJLCJLC":
                        count += 1
        return count

    def generate_fabrication_data(self):
        """Mirror of JLCPCBTools.generate_fabrication_data.

        The GUI shows "Continue?" dialogs for the two checks; here they become
        GitHub warnings and generation continues, as if OK had been clicked.
        """
        warnings = self.fabrication.get_part_consistency_warnings()
        if warnings:
            _gh_warning(
                "Items with identical LCSC number but different values: "
                + warnings.replace("\n", " ")
            )
        if self.settings.get("general", {}).get("order_number"):
            count = self.count_order_number_placeholders()
            if count == 0:
                _gh_warning("JLC order/serial number placeholder not present.")
            elif count > 1:
                _gh_warning("Multiple order/serial number placeholders present.")
        self.fabrication.fill_zones()
        # The plugin's layer dropdown defaults to "Auto", which passes None.
        self.fabrication.generate_geber(None)
        self.fabrication.generate_excellon()
        self.fabrication.zip_gerber_excellon()
        self.fabrication.generate_cpl()
        self.fabrication.generate_bom()


def _gh_warning(message):
    print(f"::warning title=JLCPCB plugin::{message}", flush=True)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    plugin_dir = os.path.abspath(sys.argv[1])
    board_path = os.path.abspath(sys.argv[2])

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(levelname)s %(name)s: %(message)s",
    )
    errors = _ErrorCounter()
    logging.getLogger().addHandler(errors)

    import pcbnew  # pylint: disable=import-error,import-outside-toplevel

    print(f"KiCad {pcbnew.Version()}, board {board_path}", flush=True)
    board = pcbnew.LoadBoard(board_path)
    tools = HeadlessJLCPCBTools(plugin_dir, board)
    tools.generate_fabrication_data()

    # File names as written by Fabrication.zip_gerber_excellon / generate_cpl / generate_bom
    stem = os.path.splitext(tools.fabrication.filename)[0]
    outdir = tools.fabrication.outputdir
    outputs = {
        "gerber_zip": os.path.join(outdir, f"GERBER-{stem}.zip"),
        "cpl_csv": os.path.join(outdir, f"CPL-{stem}.csv"),
        "bom_csv": os.path.join(outdir, f"BOM-{stem}.csv"),
    }
    missing = [p for p in outputs.values() if not os.path.isfile(p) or os.path.getsize(p) == 0]
    if missing:
        print(f"::error::Missing or empty output files: {missing}", flush=True)
        return 1
    if errors.count:
        print(f"::error::The plugin logged {errors.count} error(s), see log above.", flush=True)
        return 1
    for name, path in outputs.items():
        print(f"{name}: {path} ({os.path.getsize(path)} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
