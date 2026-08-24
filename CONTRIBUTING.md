# Contributing

v0.2.0 的公开仓库分发 CPython 3.13 字节码，不公开模型源码。欢迎提交文档、
验证用例、可复现问题和不含受限源码的改进建议；不要提交反编译、反汇编或其他
逆向得到的材料。

提交前请：

1. 说明改动是 bug fix、复现、适配、混合还是新设计；
2. 为公式、单位、参数范围和数据来源提供可追溯依据；
3. 使用 CPython 3.13 安装 `requirements-dev.txt`，运行 `python -m pytest -q`；
4. 运行 `python -X utf8 scripts/full_chain.pyc --demo --out outputs/contribution-smoke`；
5. 不提交真实业务数据、凭据、个人信息或生成结果；
6. 在说明中区分软件 smoke test、数值检查和专业水文验证。

涉及核心方程、单位或守恒关系的改动必须由有权访问原始源码的维护者重建字节码，
并附带验证数据、来源和假设说明。公开测试通过不等于流域率定或专业验收。
