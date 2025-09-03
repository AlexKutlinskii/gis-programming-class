# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
                                 QDoubleSpinBox, QHBoxLayout, QPushButton, QMessageBox, QWidget)
from qgis.core import QgsProject, QgsCoordinateReferenceSystem
from qgis.utils import iface
import processing

class KutlinskiyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kutlinskiy — Reproject & Simplify")
        self.resize(400, 120)
        layout = QVBoxLayout()

        # Layer selector
        hl1 = QHBoxLayout()
        hl1.addWidget(QLabel("Select vector layer:"))
        self.layer_combo = QComboBox()
        hl1.addWidget(self.layer_combo)
        layout.addLayout(hl1)

        # Reproject checkbox-like (using combo for yes/no)
        hl2 = QHBoxLayout()
        hl2.addWidget(QLabel("Reproject to EPSG:4326?"))
        self.reproj_combo = QComboBox()
        self.reproj_combo.addItems(["Yes", "No"])
        hl2.addWidget(self.reproj_combo)
        layout.addLayout(hl2)

        # Tolerance
        hl3 = QHBoxLayout()
        hl3.addWidget(QLabel("Simplify tolerance (map units):"))
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.0, 1e6)
        self.tolerance_spin.setDecimals(6)
        self.tolerance_spin.setValue(0.0001)
        hl3.addWidget(self.tolerance_spin)
        layout.addLayout(hl3)

        # Buttons
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("Run")
        self.close_btn = QPushButton("Close")
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.run_btn.clicked.connect(self.accept)
        self.close_btn.clicked.connect(self.reject)

        self._populate_layers()

    def _populate_layers(self):
        self.layer_combo.clear()
        layers = [lyr for lyr in QgsProject.instance().mapLayers().values() if lyr.type() == lyr.VectorLayer]
        for lyr in layers:
            self.layer_combo.addItem(lyr.name(), lyr.id())

    def selected_layer(self):
        layer_id = self.layer_combo.currentData()
        if not layer_id:
            return None
        return QgsProject.instance().mapLayer(layer_id)

class KutlinskiyPlugin:
    def __init__(self, iface_param):
        self.iface = iface_param
        self.action = None
        self.toolbar = None

    def initGui(self):
        self.action = self.iface.addPluginToMenu("&Kutlinskiy", None)  # menu entry (no icon)
        # also add a small toolbar button:
        self.toolbar = self.iface.addToolBar("Kutlinskiy")
        self.action = self.toolbar.addAction("Kutlinskiy")
        self.action.triggered.connect(self.run)

    def unload(self):
        # remove toolbar and menu
        try:
            self.iface.removePluginMenu("&Kutlinskiy", self.action)
            self.iface.removeToolBarIcon(self.action)
        except Exception:
            pass

    def run(self):
        dlg = KutlinskiyDialog(parent=iface.mainWindow())
        # refresh layer list each time
        dlg._populate_layers()
        if dlg.exec_() != QDialog.Accepted:
            return

        layer = dlg.selected_layer()
        if layer is None:
            QMessageBox.warning(iface.mainWindow(), "Kutlinskiy", "No vector layer selected.")
            return

        do_reproject = (dlg.reproj_combo.currentText() == "Yes")
        tol = float(dlg.tolerance_spin.value())

        try:
            # Step 1: optionally reproject to EPSG:4326
            current_input = layer
            if do_reproject:
                params = {
                    'INPUT': layer,
                    'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:4326'),
                    'OUTPUT': 'memory:'
                }
                res = processing.run('native:reprojectlayer', params)
                intermediate = res['OUTPUT']
            else:
                intermediate = layer

            # Step 2: simplify geometries
            params2 = {
                'INPUT': intermediate,
                'METHOD': 0,          # 0 = distance (Douglas-Peucker)
                'TOLERANCE': tol,
                'OUTPUT': 'memory:'
            }
            # run and load results into QGIS TO MAP
            processing.runAndLoadResults('native:simplifygeometries', params2)

            QMessageBox.information(iface.mainWindow(), "Kutlinskiy", "Operation finished. Result added to map (temporary layer).")

        except Exception as e:
            QMessageBox.critical(iface.mainWindow(), "Kutlinskiy: Error", str(e))
