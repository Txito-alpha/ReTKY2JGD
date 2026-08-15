# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QRadioButton, QVBoxLayout, QWidget
)
from qgis.core import QgsMapLayerProxyModel
from qgis.gui import QgsMapLayerComboBox


class ReTKY2JGDDialog(QDialog):
    def __init__(self, iface, zones, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.zones = zones
        self.setWindowTitle('ReTKY2JGD')
        self.resize(760, 420)

        self.single_radio = QRadioButton('単一レイヤを変換', self)
        self.batch_radio = QRadioButton('ディレクトリ以下のShapefileを一括変換', self)
        self.single_radio.setChecked(True)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.single_radio)
        mode_row.addWidget(self.batch_radio)
        mode_row.addStretch(1)

        self.layer_combo = QgsMapLayerComboBox(self)
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        if iface.activeLayer() is not None:
            self.layer_combo.setLayer(iface.activeLayer())
        self.output_edit = QLineEdit(self)
        self.output_edit.setPlaceholderText('GeoPackage（.gpkg）またはShapefile（.shp）')
        output_browse = QPushButton('参照...', self)
        output_browse.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(output_browse)
        self.single_box = QGroupBox('単一変換', self)
        single_form = QFormLayout(self.single_box)
        single_form.addRow('入力ベクタレイヤ:', self.layer_combo)
        single_form.addRow('出力ファイル:', output_row)

        self.input_dir_edit = QLineEdit(self)
        input_dir_browse = QPushButton('参照...', self)
        input_dir_browse.clicked.connect(self._browse_input_dir)
        input_dir_row = QHBoxLayout()
        input_dir_row.addWidget(self.input_dir_edit, 1)
        input_dir_row.addWidget(input_dir_browse)

        self.output_dir_edit = QLineEdit(self)
        output_dir_browse = QPushButton('参照...', self)
        output_dir_browse.clicked.connect(self._browse_output_dir)
        output_dir_row = QHBoxLayout()
        output_dir_row.addWidget(self.output_dir_edit, 1)
        output_dir_row.addWidget(output_dir_browse)

        self.suffix_edit = QLineEdit('_convert', self)
        self.suffix_edit.setPlaceholderText('空欄の場合は元のファイル名')
        self.batch_box = QGroupBox('ディレクトリ一括変換', self)
        batch_form = QFormLayout(self.batch_box)
        batch_form.addRow('入力ディレクトリ:', input_dir_row)
        batch_form.addRow('出力ディレクトリ:', output_dir_row)
        batch_form.addRow('ファイル名末尾:', self.suffix_edit)
        batch_note = QLabel('入力ディレクトリ以下の .shp を再帰的に処理し、出力先へ同じフォルダ構成を作成します。', self.batch_box)
        batch_note.setWordWrap(True)
        batch_form.addRow('', batch_note)

        self.zone_combo = QComboBox(self)
        for z in zones:
            label = '{0}系  EPSG:{1}  原点 {2:g}, {3:g}  {4}'.format(
                z['zone_roman'], z['epsg'], z['lat_0'], z['lon_0'], z['area_summary'])
            self.zone_combo.addItem(label, z)

        warning = QLabel(
            '注意: 入力のCRS表示は参照せず、選択したJGD2000平面直角座標系を割り当てます。\n'
            '対象は「簡易変換により日本測地系から世界測地系へ変換済み」のデータに限定してください。', self)
        warning.setWordWrap(True)
        warning.setStyleSheet('color: #8a4b00; font-weight: bold;')

        common_form = QFormLayout()
        common_form.addRow('座標系:', self.zone_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText('実行')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(warning)
        layout.addLayout(mode_row)
        layout.addWidget(self.single_box)
        layout.addWidget(self.batch_box)
        layout.addLayout(common_form)
        layout.addWidget(buttons)

        self.single_radio.toggled.connect(self._update_mode)
        self._update_mode()
        self._select_zone_from_layer()

    def _update_mode(self):
        single = self.single_radio.isChecked()
        self.single_box.setEnabled(single)
        self.batch_box.setEnabled(not single)

    def _select_zone_from_layer(self):
        layer = self.layer_combo.currentLayer()
        if not layer:
            return
        authid = layer.crs().authid().upper()
        for i, z in enumerate(self.zones):
            if authid == 'EPSG:{0}'.format(z['epsg']):
                self.zone_combo.setCurrentIndex(i)
                break

    def _browse_output(self):
        path, selected = QFileDialog.getSaveFileName(
            self, '出力ファイル', self.output_edit.text(),
            'GeoPackage (*.gpkg);;Shapefile (*.shp)')
        if path:
            if not os.path.splitext(path)[1]:
                path += '.gpkg' if 'GeoPackage' in selected else '.shp'
            self.output_edit.setText(path)

    def _browse_input_dir(self):
        path = QFileDialog.getExistingDirectory(self, '入力ディレクトリ', self.input_dir_edit.text())
        if path:
            self.input_dir_edit.setText(path)
            if not self.output_dir_edit.text().strip():
                self.output_dir_edit.setText(os.path.join(os.path.dirname(path), os.path.basename(path) + '_converted'))

    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, '出力ディレクトリ', self.output_dir_edit.text())
        if path:
            self.output_dir_edit.setText(path)

    def values(self):
        return {
            'mode': 'single' if self.single_radio.isChecked() else 'batch',
            'layer': self.layer_combo.currentLayer(),
            'zone': self.zone_combo.currentData(),
            'output': self.output_edit.text().strip(),
            'input_dir': self.input_dir_edit.text().strip(),
            'output_dir': self.output_dir_edit.text().strip(),
            'suffix': self.suffix_edit.text(),
        }

    def accept(self):
        values = self.values()
        if values['mode'] == 'single':
            if values['layer'] is None:
                QMessageBox.warning(self, '入力不足', '入力ベクタレイヤを選択してください。')
                return
            if not values['output']:
                QMessageBox.warning(self, '入力不足', '出力ファイルを指定してください。')
                return
            if os.path.splitext(values['output'])[1].lower() not in ('.gpkg', '.shp'):
                QMessageBox.warning(self, '出力形式', '出力は .gpkg または .shp を指定してください。')
                return
        else:
            input_dir = os.path.abspath(values['input_dir'])
            output_dir = os.path.abspath(values['output_dir'])
            if not os.path.isdir(input_dir):
                QMessageBox.warning(self, '入力不足', '有効な入力ディレクトリを指定してください。')
                return
            if not values['output_dir']:
                QMessageBox.warning(self, '入力不足', '出力ディレクトリを指定してください。')
                return
            if input_dir == output_dir:
                QMessageBox.warning(self, '出力先エラー', '出力ディレクトリは入力ディレクトリと別にしてください。')
                return
            try:
                common = os.path.commonpath([input_dir, output_dir])
            except ValueError:
                common = ''
            if common == input_dir:
                QMessageBox.warning(
                    self, '出力先エラー',
                    '出力ディレクトリを入力ディレクトリの内部には作成できません。\n'
                    '一括処理への再取り込みを防ぐため、入力ディレクトリの外側を指定してください。')
                return
            has_shapefile = any(
                name.lower().endswith('.shp')
                for root, dirs, files in os.walk(input_dir)
                for name in files)
            if not has_shapefile:
                QMessageBox.warning(self, '対象なし', '入力ディレクトリ以下にShapefileがありません。')
                return
            invalid = set('/\\:*?"<>|')
            if any(ch in invalid for ch in values['suffix']):
                QMessageBox.warning(self, 'ファイル名エラー', '末尾文字列にファイル名として使用できない文字が含まれています。')
                return
        super().accept()
