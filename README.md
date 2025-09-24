# ReTKY2JGD

日本測地系（**Tokyo Datum / TOKYO**）から世界測地系（**JGD2000**）へ簡易変換された国有林GISデータを、
一度逆変換したのち、**正式なTKY2JGD変換**を適用し、より正確な座標に補正するためのリポジトリです。

---

## 背景

* 林野庁がG空間情報センターで公開する[国有林GISデータ（2025.3公開）](https://www.geospatial.jp/ckan/dataset/a45)は、
  一部が**簡易変換**（座標系の3パラメータ近似）によりJGD2000へ変換されています。
* 正式な座標系変換（TKY2JGD.gsbによる格子補正）を行うには、いったん元のTOKYO系に戻し、再度TKY2JGDを適用する必要があります。
* 公式データは今後修正される可能性がありますが、本データを用いて作成した成果が紙ベースで残されている場合等では、補正のために同様の作業が必要となります。  

---

## 機能

1. **平面直角座標系ごとのmodel3ファイル**

   * QGISモデルデザイナーで使用
   * ファイル名は「平面直角座標系_x系_EPSGコード.model3」
2. **Excelマクロ**

   * QGISモデルデザイナーで定義した処理モデルと関連ファイルの一覧を自動取得
   * バッチ処理用のファイルリストを生成
3. **補正済みGISデータ**

   * 上記モデルで処理したサンプルデータ（**[国有林GISデータ](https://www.geospatial.jp/ckan/dataset/a45)の補正版**)です。
   * 本補正はあくまで機械的な補正であり、使用の際は**測量成果の確認が必須**です。

---

## 主要ファイル

| パス                                  | 内容                    |
| ----------------------------------- | --------------------- |
| `/source/ReTKY2JGD_batch_list.xlsm` | QGISモデルデザイナー用Excelマクロ |
| `/data/`                            | 補正後の国有林GISデータ（fgb）    |

---

## 依存・利用環境

* **QGIS** 3.34 以降
* **Excel** 2016 以降（マクロ有効）

---

## 使い方（概要）

使用にあたり、**tohka氏が公開している [TKY2JGD.gsb](https://github.com/tohka/JapanGridShift)** が別途必要となります。
1. `/macro/ReTKY2JGD_batch_list.xlsm` を開き、対象ディレクトリを指定してバッチリストを生成
2. QGISのモデルデザイナーでリストを読み込み、TKY2JGD.gsbを参照して変換実行
3. `/data/` に出力された成果を確認

※詳細な操作手順は `docs/usage_guide.md` を参照してください。

---

## 注意事項

* 本リポジトリの補正は**日本測地系から世界測地系への簡易補正データの再変換のみを行う**ものであり、touhokutaiheiyouoki2011等の地震パラメータについては別途適用する必要があります。
* このことから、本データによる変換結果を**測量成果としてそのまま使用することを想定していません**。使用にあたっては必ず現地測量や公式成果で確認してください。
* またTKY2JGD.gsbの使用にあたり、tohka氏の[JapanGridShift](https://github.com/tohka/JapanGridShift) の注意事項についても併せてご確認ください。
  

---

## ライセンス

* Excelマクロデータ: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

  * 元データ: 林野庁「国有林GISデータ（2025.3公開）」を本リポジトリで変換
  * 改変: ReTKY2JGDプロジェクト
* ソースコード: MIT License

* TKY2JGDの[座標補正パラメータ](https://www.gsi.go.jp/sokuchikijun/sokuchikijun41012.html#zahyo)は[国土地理院コンテンツ利用規約](https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html)に基づき国土地理院が公開しているデータです。


---

## 引用

本リポジトリを利用する場合は以下のように引用してください。

```
ReTKY2JGD: Re-conversion from Tokyo Datum to JGD2000 with TKY2JGD
https://github.com/Txito-alpha/ReTKY2JGD
```

---

地理情報の正確性向上や過去データの整備・再利用に役立つよう、
Pull Request・Issueでの改善提案を歓迎します。
