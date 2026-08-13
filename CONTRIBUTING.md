# Contributing

感谢贡献。请在提交前：

1. 说明改动是 bug fix、复现、适配、混合还是新设计；
2. 为公式、单位、参数范围和数据来源提供可追溯依据；
3. 运行 `python -m pytest -q` 和 `python -m py_compile scripts/scs_unit_hydrograph.py`；
4. 不提交真实业务数据、凭据、个人信息或生成结果；
5. 在说明中区分软件 smoke test、数值检查和专业水文验证。

涉及核心方程、单位或守恒关系的改动需要附带验证数据和假设说明。
