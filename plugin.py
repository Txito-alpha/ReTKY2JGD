# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction, QApplication, QMessageBox, QProgressDialog, QToolBar
)
from qgis.core import (
    Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsProcessingContext,
    QgsProcessingException, QgsProcessingFeedback, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer
)
import processing

from .dialog import ReTKY2JGDDialog
from .zones import load_zones


class ReTKY2JGDPlugin:
    MENU_NAME = '国有林ツール'
    TOOLBAR_OBJECT_NAME = 'NationalForestToolbar'
    TOOLBAR_TITLE = '国有林ツールバー'

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.toolbar = None
        self.created_toolbar = False
        self.zones = load_zones(self.plugin_dir)

    def tr(self, text):
        return QCoreApplication.translate('ReTKY2JGD', text)

    def initGui(self):
        icon = QIcon(os.path.join(self.plugin_dir, 'icon.png'))
        self.action = QAction(icon, self.tr('TKY2JGDで再変換'), self.iface.mainWindow())
        self.action.setObjectName('ReTKY2JGDAction')
        self.action.setToolTip(self.tr('簡易変換済みデータをTKY2JGD.gsbで再変換'))
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.MENU_NAME, self.action)

        self.toolbar = self.iface.mainWindow().findChild(QToolBar, self.TOOLBAR_OBJECT_NAME)
        if self.toolbar is None:
            self.toolbar = self.iface.addToolBar(self.TOOLBAR_TITLE)
            self.toolbar.setObjectName(self.TOOLBAR_OBJECT_NAME)
            self.toolbar.setWindowTitle(self.TOOLBAR_TITLE)
            self.created_toolbar = True
        self.toolbar.addAction(self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(self.MENU_NAME, self.action)
            if self.toolbar is not None:
                self.toolbar.removeAction(self.action)
            self.action.deleteLater()
        if self.created_toolbar and self.toolbar is not None and not self.toolbar.actions():
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
        self.action = None
        self.toolbar = None

    def run(self):
        dialog = ReTKY2JGDDialog(self.iface, self.zones)
        if not dialog.exec_():
            return
        values = dialog.values()
        try:
            grid_path = self._find_grid_file()
            if values['mode'] == 'batch':
                self._execute_batch(
                    values['input_dir'], values['output_dir'], values['suffix'],
                    values['zone'], grid_path)
            else:
                self._execute(values['layer'], values['zone'], values['output'], grid_path)
        except Exception as exc:
            QMessageBox.critical(self.iface.mainWindow(), 'ReTKY2JGD エラー', str(exc))

    def _execute_batch(self, input_dir, output_dir, suffix, zone, grid_path):
        input_dir = os.path.abspath(input_dir)
        output_dir = os.path.abspath(output_dir)
        if input_dir == output_dir:
            raise ValueError('出力ディレクトリは入力ディレクトリと別にしてください。')
        try:
            if os.path.commonpath([input_dir, output_dir]) == input_dir:
                raise ValueError('出力ディレクトリは入力ディレクトリの外側を指定してください。')
        except ValueError as exc:
            if str(exc).startswith('出力ディレクトリ'):
                raise

        os.makedirs(output_dir, exist_ok=True)
        source_files = []
        for current_dir, dir_names, file_names in os.walk(input_dir, followlinks=False):
            dir_names[:] = [
                name for name in dir_names
                if not os.path.islink(os.path.join(current_dir, name))]
            relative_dir = os.path.relpath(current_dir, input_dir)
            target_dir = output_dir if relative_dir == '.' else os.path.join(output_dir, relative_dir)
            os.makedirs(target_dir, exist_ok=True)
            for file_name in file_names:
                if file_name.lower().endswith('.shp'):
                    source_files.append(os.path.join(current_dir, file_name))

        source_files.sort(key=lambda value: value.lower())
        total = len(source_files)
        progress = QProgressDialog(
            '一括変換を準備しています...', 'キャンセル', 0, total * 3,
            self.iface.mainWindow())
        progress.setWindowTitle('ReTKY2JGD 一括変換')
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)
        QApplication.processEvents()

        feedback = QgsProcessingFeedback()
        progress.canceled.connect(feedback.cancel)
        completed = []
        failures = []
        canceled = False

        try:
            for index, source in enumerate(source_files):
                QApplication.processEvents()
                if progress.wasCanceled() or feedback.isCanceled():
                    canceled = True
                    break

                relative_source = os.path.relpath(source, input_dir)
                relative_parent = os.path.dirname(relative_source)
                target_parent = output_dir if not relative_parent else os.path.join(output_dir, relative_parent)
                os.makedirs(target_parent, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(source))[0]
                output = os.path.join(target_parent, base_name + suffix + '.shp')
                layer = QgsVectorLayer(source, base_name, 'ogr')
                if hasattr(layer, 'setProviderEncoding'):
                    layer.setProviderEncoding('Shift_JIS')
                if not layer.isValid():
                    failures.append('{0}: 読み込み失敗'.format(relative_source))
                    progress.setValue((index + 1) * 3)
                    continue

                try:
                    self._execute(
                        layer, zone, output, grid_path,
                        add_to_project=False, show_message=False,
                        feedback=feedback, progress_dialog=progress,
                        progress_base=index * 3, progress_label=relative_source)
                    completed.append(output)
                except QgsProcessingException as exc:
                    if feedback.isCanceled() or progress.wasCanceled():
                        canceled = True
                        break
                    failures.append('{0}: {1}'.format(relative_source, str(exc)))
                except Exception as exc:
                    if feedback.isCanceled() or progress.wasCanceled():
                        canceled = True
                        break
                    failures.append('{0}: {1}'.format(relative_source, str(exc)))
                progress.setValue((index + 1) * 3)
        finally:
            progress.close()

        if canceled:
            QMessageBox.information(
                self.iface.mainWindow(), '一括変換をキャンセルしました',
                '{0}件中{1}件の変換完了後に停止しました。\n'
                '処理中だったファイルの不完全な出力は削除を試みました。\n出力先: {2}'.format(
                    total, len(completed), output_dir))
            return

        summary = '{0}件中{1}件を変換しました。\n出力先: {2}'.format(
            total, len(completed), output_dir)
        if failures:
            details = '\n'.join(failures[:10])
            if len(failures) > 10:
                details += '\nほか{0}件'.format(len(failures) - 10)
            QMessageBox.warning(
                self.iface.mainWindow(), '一括変換結果',
                summary + '\n\n失敗: {0}件\n{1}'.format(len(failures), details))
        else:
            QMessageBox.information(self.iface.mainWindow(), '一括変換完了', summary)

    def _find_grid_file(self):
        candidates = [
            os.path.join(self.plugin_dir, 'data', 'TKY2JGD.gsb'),
            os.path.join(self.plugin_dir, 'data', 'tky2jgd.gsb'),
        ]
        try:
            proj_path = QgsApplication.projPath()
            candidates.extend([
                os.path.join(proj_path, 'TKY2JGD.gsb'),
                os.path.join(proj_path, 'tky2jgd.gsb'),
            ])
        except Exception:
            pass
        for path in candidates:
            if path and os.path.isfile(path):
                return os.path.abspath(path).replace('\\', '/')
        raise FileNotFoundError(
            'TKY2JGD.gsb が見つかりません。\n'
            'グリッドファイルを次の場所へ配置してください。\n{0}'.format(
                os.path.join(self.plugin_dir, 'data', 'TKY2JGD.gsb')))

    @staticmethod
    def _format_number(value):
        return ('{0:.9f}'.format(float(value))).rstrip('0').rstrip('.')

    @staticmethod
    def _remove_shapefile_set(output):
        if os.path.splitext(output)[1].lower() != '.shp':
            return
        stem = os.path.splitext(output)[0]
        for extension in ('.shp', '.shx', '.dbf', '.prj', '.cpg', '.qpj'):
            path = stem + extension
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

    def _write_output(self, layer_or_path, output, target_crs):
        layer = layer_or_path
        if not hasattr(layer_or_path, 'isValid'):
            layer = QgsVectorLayer(str(layer_or_path), '変換結果', 'ogr')
        if not layer.isValid():
            raise RuntimeError('一時変換結果を読み込めませんでした。')

        extension = os.path.splitext(output)[1].lower()
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        options.driverName = 'ESRI Shapefile' if extension == '.shp' else 'GPKG'
        options.fileEncoding = 'Shift_JIS' if extension == '.shp' else 'UTF-8'
        if extension == '.gpkg':
            options.layerName = os.path.splitext(os.path.basename(output))[0]

        transform_context = QgsProject.instance().transformContext()
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, output, transform_context, options)
        error_code = result[0]
        error_message = result[1] if len(result) > 1 else ''
        if error_code != QgsVectorFileWriter.NoError:
            raise RuntimeError('出力ファイルの保存に失敗しました。\n{0}'.format(error_message))

        # The writer normally creates a .cpg. Write it explicitly so that
        # other GIS software also interprets DBF attributes as Shift_JIS.
        if extension == '.shp':
            cpg_path = os.path.splitext(output)[0] + '.cpg'
            with open(cpg_path, 'w', encoding='ascii', newline='') as stream:
                stream.write('Shift_JIS')
        return output

    def _execute(self, layer, zone, output, grid_path, add_to_project=True, show_message=True,
                 feedback=None, progress_dialog=None, progress_base=0, progress_label=""):
        # Shapefile input is expected to use Shift_JIS. Set the provider encoding
        # before Processing reads attribute values, preventing mojibake.
        source_path = layer.source().split('|', 1)[0].lower()
        if source_path.endswith('.shp') and hasattr(layer, 'setProviderEncoding'):
            layer.setProviderEncoding('Shift_JIS')

        epsg = int(zone['epsg'])
        lat_0 = self._format_number(zone['lat_0'])
        lon_0 = self._format_number(zone['lon_0'])
        target_crs = QgsCoordinateReferenceSystem('EPSG:{0}'.format(epsg))
        tokyo_crs = QgsCoordinateReferenceSystem('EPSG:4301')
        if not target_crs.isValid() or not tokyo_crs.isValid():
            raise RuntimeError('必要なCRSをQGISで作成できません。EPSGデータベースを確認してください。')

        # The input coordinates are treated as JGD2000 plane rectangular values,
        # regardless of the CRS metadata currently attached to the layer.
        reverse_pipeline = (
            '+proj=pipeline '
            '+step +inv +proj=tmerc +lat_0={lat} +lon_0={lon} +k=0.9999 +x_0=0 +y_0=0 +ellps=GRS80 '
            '+step +proj=push +v_3 '
            '+step +proj=cart +ellps=GRS80 '
            '+step +proj=helmert +x=146.414 +y=-507.337 +z=-680.507 '
            '+step +inv +proj=cart +ellps=bessel '
            '+step +proj=pop +v_3 '
            '+step +proj=unitconvert +xy_in=rad +xy_out=deg'
        ).format(lat=lat_0, lon=lon_0)

        grid_token = grid_path
        if ' ' in grid_token:
            grid_token = '"{0}"'.format(grid_token)
        forward_pipeline = (
            '+proj=pipeline '
            '+step +proj=unitconvert +xy_in=deg +xy_out=rad '
            '+step +proj=hgridshift +grids={grid} '
            '+step +proj=tmerc +lat_0={lat} +lon_0={lon} +k=0.9999 +x_0=0 +y_0=0 +ellps=GRS80'
        ).format(grid=grid_token, lat=lat_0, lon=lon_0)

        feedback = feedback or QgsProcessingFeedback()
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())
        def update_progress(step, description):
            if progress_dialog is not None:
                progress_dialog.setLabelText(
                    '{0}\n{1}/3: {2}'.format(progress_label, step, description))
                progress_dialog.setValue(progress_base + step - 1)
                QApplication.processEvents()
            if feedback.isCanceled():
                raise QgsProcessingException('処理がキャンセルされました。')

        try:
            update_progress(1, 'CRSを割り当てています')
            assigned = processing.run('native:assignprojection', {
                'INPUT': layer,
                'CRS': target_crs,
                'OUTPUT': 'TEMPORARY_OUTPUT',
            }, context=context, feedback=feedback)
            update_progress(2, 'Tokyo地理座標へ逆変換しています')
            tokyo = processing.run('native:reprojectlayer', {
                'INPUT': assigned['OUTPUT'],
                'TARGET_CRS': tokyo_crs,
                'OPERATION': reverse_pipeline,
                'OUTPUT': 'TEMPORARY_OUTPUT',
            }, context=context, feedback=feedback)
            update_progress(3, 'TKY2JGDで再変換しています')
            result = processing.run('native:reprojectlayer', {
                'INPUT': tokyo['OUTPUT'],
                'TARGET_CRS': target_crs,
                'OPERATION': forward_pipeline,
                'OUTPUT': 'TEMPORARY_OUTPUT',
            }, context=context, feedback=feedback)
        finally:
            pass

        if feedback.isCanceled():
            self._remove_shapefile_set(output)
            raise QgsProcessingException('処理がキャンセルされました。')
        transformed = result['OUTPUT']
        result_path = self._write_output(transformed, output, target_crs)
        name = os.path.splitext(os.path.basename(output))[0]
        out_layer = QgsVectorLayer(result_path, name, 'ogr')
        if result_path.lower().endswith('.shp') and hasattr(out_layer, 'setProviderEncoding'):
            out_layer.setProviderEncoding('Shift_JIS')
        if not out_layer.isValid():
            raise RuntimeError('変換処理は終了しましたが、出力レイヤを読み込めませんでした。\n{0}'.format(result_path))
        if add_to_project:
            QgsProject.instance().addMapLayer(out_layer)
        if show_message:
            self.iface.messageBar().pushMessage(
                'ReTKY2JGD', '変換が完了しました: EPSG:{0}'.format(epsg),
                level=Qgis.Success, duration=8)
        return result_path
