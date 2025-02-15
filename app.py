from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def volatility():
    error_message = None
    volatility_data = None
    graph_url = None

    if request.method == "POST":
        try:
            ticker = request.form["ticker"]
            period = request.form["period"]
            interval = request.form["interval"]

            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval, auto_adjust=True)

            if df.empty:
                error_message = "無効な銘柄コードが入力されました。正しい銘柄コードを入力してください。"
            else:
                # 変動幅の計算
                df["Volatility"] = df["High"] - df["Low"]

                mean_volatility = df["Volatility"].mean()
                median_volatility = df["Volatility"].median()
                top_5_volatility = df["Volatility"].nlargest(5).tolist()

                # グラフ作成
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.hist(df["Volatility"], bins=20, color="blue", alpha=0.7)
                ax.set_title("Volatility Distribution")
                ax.set_xlabel("Volatility (Price Range)")
                ax.set_ylabel("Frequency")

                img = io.BytesIO()
                plt.tight_layout()
                plt.savefig(img, format="png")
                img.seek(0)
                graph_url = base64.b64encode(img.getvalue()).decode()
                plt.close(fig)

                # 結果データ
                volatility_data = {
                    "mean": round(mean_volatility, 2),
                    "median": round(median_volatility, 2),
                    "top_5": [round(v, 2) for v in top_5_volatility],
                }

        except Exception as e:
            error_message = f"エラーが発生しました: {e}"

    return render_template("index.html", error_message=error_message, volatility_data=volatility_data, graph_url=graph_url)

if __name__ == "__main__":
    app.run(debug=True)
