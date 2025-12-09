from . import tests

def try_load_k2(env):
    import os
    os.environ["FISCAL_YEAR"] = "2022-12"
    env["account.chart.template"].try_load_k2()