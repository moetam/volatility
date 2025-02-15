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
    graph_url_up = None
    graph_url_down = None

    if request.method == "POST":
        try:
            ticker = request.form["ticker"]
            period = request.form["period"]
            interval = request.form["interval"]
            tick_size = float(request.form["tick_size"])

            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval, auto_adjust=True)

            if df.empty:
                error_message = "読み取り不能な値が入力されているので結果を出せません。"
            else:
                    # 変動幅の計算
                df["Volatility"] = df["High"] - df["Low"]
                # 呼値で丸め
                df["Volatility"] = (df["Volatility"] / tick_size).round() * tick_size

                # 陽線・陰線を分割
                df["Up"] = df["Close"] > df["Open"]
                up_volatility = df[df["Up"]]["Volatility"]
                down_volatility = df[~df["Up"]]["Volatility"]

                # 平均値・中央値
                mean_up = up_volatility.mean()
                median_up = up_volatility.median()
                mean_down = down_volatility.mean()
                median_down = down_volatility.median()

                # ランキング用bin
                bin_edges = np.arange(0, max(up_volatility.max(), down_volatility.max()) + tick_size, tick_size)

                top_5_up = up_volatility.value_counts(bins=bin_edges).nlargest(5).to_dict()
                top_5_down = down_volatility.value_counts(bins=bin_edges).nlargest(5).to_dict()

                # グラフ描画
                def create_graph(data, color):
                    fig, ax = plt.subplots(figsize=(10, 4))
                    bar_data = data.value_counts(bins=bin_edges).sort_index()
                    ax.bar(bar_data.index.astype(str), bar_data, color=color, alpha=0.7, width=1)
                    ax.set_title("Volatility")
                    ax.set_xlabel("Volatility Range")
                    ax.set_ylabel("Count")
                    # X軸ラベルをbin_edgesから10個刻みで設定
                    ax.set_xticks(bin_edges[::10])
                    ax.set_xticklabels([f"{round(x, 2)}" for x in bin_edges[::10]])
                    plt.xticks(rotation=45)

                    img = io.BytesIO()
                    plt.tight_layout()
                    plt.savefig(img, format="png")
                    img.seek(0)
                    graph_url = base64.b64encode(img.getvalue()).decode()
                    plt.close(fig)
                    return graph_url

                graph_url_up = create_graph(up_volatility, "red")
                graph_url_down = create_graph(down_volatility, "green")

                # 結果データ
                volatility_data = {
                    "mean_up": round(mean_up, 2),
                    "median_up": round(median_up, 2),
                    "mean_down": round(mean_down, 2),
                    "median_down": round(median_down, 2),
                    "top_5_up": {f"{k.left:.2f}-{k.right:.2f}": int(v) for k, v in top_5_up.items()},
                    "top_5_down": {f"{k.left:.2f}-{k.right:.2f}": int(v) for k, v in top_5_down.items()}
                }

        except Exception as e:
            error_message = f"エラーが発生しました: {e}"

    return render_template("index.html", error_message=error_message, volatility_data=volatility_data, graph_url_up=graph_url_up, graph_url_down=graph_url_down)

if __name__ == "__main__":
    app.run(debug=True)
