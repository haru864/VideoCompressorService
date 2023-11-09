# Video Compress Service
mp4ファイルに対して以下いずれかの処理を実行します。
* 圧縮
* 解像度の変更
* 縦横比の変更
* オーディオファイルへの変換
* 指定した時間範囲の切り取り

# 使い方
サーバーを起動します。<br>
使用するアドレスとポート番号は config/config.json で指定します。

```python
python3 src/server.py
```

クライアントを起動します。
```python
python3 src/client.py
```

クライアントの画面に表示される指示に従って操作すると、<br>
加工後のファイルがクライアント側に作成されます。

