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
            if "." not in ticker:
                # 「.」が入っていなければ、.T を自動追加
                ticker += ".T"
            period = request.form["period"]
            interval = request.form["interval"]
            tick_size = float(request.form["tick_size"])

            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval, auto_adjust=True)

            if df.empty:
                error_message = "読み取り不能な値が入力されているので結果を出せません。byもえちゃん"
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
                def create_graph(data, color, tick_size):
                    # bin_edgesを作成（0～最大値までtick_size刻み）
                    data_max = data.max()
                    if data_max == 0:
                        # データが0のみの場合などを想定
                        data_max = tick_size
                    bin_edges = np.arange(0, data_max + tick_size, tick_size)

                    # 区間ごとにカウント
                    bar_data = data.value_counts(bins=bin_edges).sort_index()
                    intervals = bar_data.index  # IntervalIndex

                    # X座標を「区間の中点」として数値で取得
                    x_vals = [iv.mid for iv in intervals]  # 各Intervalの中心値
                    y_vals = bar_data.values

                    # グラフ描画
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.bar(x_vals, y_vals, color=color, alpha=0.7, width=tick_size)

                    ax.set_title("Volatility")
                    ax.set_xlabel("Volatility Range")
                    ax.set_ylabel("Count")

                    # X軸の最大値を中点＋呼値で少し余裕を持たせる
                    x_max = x_vals[-1] + tick_size
                    ax.set_xlim(0, x_max)

                    # メモリを10刻みにする例（必要に応じて調整）
                    step = 10
                    # x_max が小さい場合にステップが大きすぎるとメモリが0だけになるので、最小1とするなど工夫
                    step = max(1, step)  

                    ax.set_xticks(np.arange(0, x_max + step, step))
                    ax.set_xticklabels([str(int(v)) for v in np.arange(0, x_max + step, step)])
                    plt.xticks(rotation=45)

                    # 画像をBase64に変換
                    img = io.BytesIO()
                    plt.tight_layout()
                    plt.savefig(img, format="png")
                    img.seek(0)
                    graph_url = base64.b64encode(img.getvalue()).decode()
                    plt.close(fig)
                    return graph_url

                graph_url_up = create_graph(up_volatility, "red", tick_size)
                graph_url_down = create_graph(down_volatility, "green", tick_size)

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
