"""Build app/content/book.json from the parsed PDF JSON, adding Chinese titles.

Usage: python3 tools/build_content.py <parsed.json>
"""
import json, sys, os

ZH = {
    "fit": "Fit / 行为面试", "deal": "交易经历", "tech": "通用技术题", "industry": "行业 / 组别技术题",
    "fit-intro": "Fit 面试准备总览", "tech-intro": "技术题说明", "industry-intro": "行业题说明", "deal-intro": "讲述交易经历",
    "the-big-5-fit-questions": "五大核心 Fit 问题", "teamwork-leadership": "团队合作 / 领导力",
    "strengths-and-weaknesses": "优点与缺点", "flaws-and-failures": "缺陷与失败",
    "recruiting-process": "招聘流程", "resume-cv": "简历 / CV", "understanding-banking": "理解投行",
    "why-banking-and-why-our-firm": "为什么投行？为什么我们？", "outside-the-box-questions": "非常规问题",
    "finance-concepts": "金融概念", "accounting-concepts": "会计 – 概念", "accounting-calculations": "会计 – 计算题",
    "equity-value-and-enterprise-value-concepts": "股权价值与企业价值 – 概念",
    "equity-value-and-enterprise-value-calculations": "股权价值与企业价值 – 计算",
    "valuation-methodologies": "估值方法", "valuation-metrics-and-multiples": "估值指标与倍数",
    "discounted-cash-flow-dcf-assumptions-and-analysi": "DCF – 假设与分析",
    "discounted-cash-flow-dcf-the-discount-rate": "DCF – 折现率",
    "merger-models-concepts": "并购模型 – 概念", "merger-models-calculations": "并购模型 – 计算",
    "lbo-models-concepts": "LBO 模型 – 概念", "lbo-models-calculations": "LBO 模型 – 计算",
    "consumer-retail": "消费 / 零售", "debt-capital-markets-dcm-and-leveraged-finance-l": "债务资本市场 (DCM) 与杠杆融资",
    "distressed-and-restructuring": "困境与重组", "equity-capital-markets-ecm": "股权资本市场 (ECM)",
    "financial-institutions-group-fig": "金融机构组 (FIG)", "financial-sponsors-group-fsg": "金融赞助人组 (FSG)",
    "healthcare-and-biotech": "医疗与生物科技", "industrials": "工业", "metals-and-mining": "金属与矿业",
    "oil-and-gas": "石油与天然气", "power-and-utilities": "电力与公用事业",
    "private-capital-advisory-secondaries": "私募资本顾问（二手份额）", "private-companies": "非上市公司",
    "project-finance-and-infrastructure": "项目融资与基础设施", "real-estate-properties": "房地产（物业）",
    "real-estate-investment-trusts-reits": "房地产投资信托 (REITs)", "renewables": "可再生能源",
    "technology-media-and-telecommunications-tmt": "科技、媒体与电信 (TMT)",
}

src = json.load(open(sys.argv[1]))
root = os.path.join(os.path.dirname(__file__), "..", "app", "content")
zh_dir = os.path.join(root, "zh")
translated = {f[:-5] for f in os.listdir(zh_dir) if f.endswith(".json")}
for p in src["parts"]:
    p["titleZh"] = ZH[p["id"]]
    for s in p["sections"]:
        s["titleZh"] = ZH[s["id"]]
        s["zh"] = s["id"] in translated
        s.pop("intro", None)
        if s["zh"]:
            z = json.load(open(os.path.join(zh_dir, s["id"] + ".json")))
            assert len(z["intro"]) == len(s["introBlocks"]), (s["id"], "intro")
            for q in s["questions"]:
                zq = z["questions"][q["id"]]
                assert len(zq["a"]) == len(q["a"]), (q["id"], len(zq["a"]), len(q["a"]))
json.dump(src, open(os.path.join(root, "book.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print("ok", sum(len(s["questions"]) for p in src["parts"] for s in p["sections"]), "questions; translated:", sorted(translated))
