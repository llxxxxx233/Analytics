"""生成模拟数据（仅用于功能演示与测试，非真实经营数据）。

输出到 data/sample/，文件名带 sample_ 前缀，data/README.md 已标注为模拟数据。
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sample"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)

IPS = ["星轨纪元", "雾都侦探", "幻境物语", "银河旅人"]
CATEGORIES = {
    "徽章/吧唧": (15, 45),
    "亚克力立牌": (25, 65),
    "挂件": (12, 35),
    "色纸": (18, 55),
    "毛绒玩偶": (48, 120),
    "文件夹": (10, 25),
}
SPECS = ["A款", "B款", "C款", "标准款", "限定款"]
CHANNELS = ["微店", "淘宝", "展会现场", "线下寄售"]
CHANNEL_W = [0.45, 0.25, 0.20, 0.10]

products = []
for i in range(18):
    ip = IPS[i % len(IPS)]
    cat, (lo, hi) = list(CATEGORIES.items())[i % len(CATEGORIES)]
    name = f"{ip}·{cat} {SPECS[i % len(SPECS)]}"
    cost = round(random.uniform(5, 45), 2)
    price = round(random.uniform(lo, hi), 2)
    weight = round(random.uniform(0.4, 2.0), 2)  # 销量热度，仅用于生成，不输出
    products.append(
        {
            "product_name": name,
            "ip": ip,
            "category": cat,
            "spec": SPECS[i % len(SPECS)],
            "cost": cost,
            "price": price,
            "weight": weight,
        }
    )

start = datetime(2026, 4, 25)
end = datetime(2026, 10, 22)
days = (end - start).days

rows = []
oid = 1
for d in range(days + 1):
    date = start + timedelta(days=d)
    n = random.randint(3, 16)
    for _ in range(n):
        p = random.choices(products, weights=[p["weight"] for p in products])[0]
        qty = random.randint(1, 4)
        amount = round(p["price"] * qty, 2)
        channel = random.choices(CHANNELS, weights=CHANNEL_W)[0]
        rows.append(
            {
                "order_id": f"SO{oid:05d}",
                "order_date": date.strftime("%Y-%m-%d"),
                "product_name": p["product_name"],
                "quantity": qty,
                "amount": amount,
                "channel": channel,
            }
        )
        oid += 1

orders = pd.DataFrame(rows)

products_df = pd.DataFrame(products)[["product_name", "ip", "category", "spec", "cost"]]
inventory_df = pd.DataFrame(
    [
        {
            "product_name": p["product_name"],
            "stock": random.randint(0, 260),
            "cost": p["cost"],
        }
        for p in products
    ]
)

orders.to_csv(OUT / "sample_orders.csv", index=False, encoding="utf-8-sig")
products_df.to_csv(OUT / "sample_products.csv", index=False, encoding="utf-8-sig")
inventory_df.to_csv(OUT / "sample_inventory.csv", index=False, encoding="utf-8-sig")

print(f"已生成模拟数据到 {OUT}")
print(f"  订单 {len(orders)} 行，商品 {len(products_df)} 个")
