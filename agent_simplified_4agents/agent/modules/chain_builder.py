STANDARD_CHAIN = ["login", "query", "export", "copy", "external_send", "delete"]


def build(candidate) -> dict:
    chain = []
    for e in sorted(candidate.events, key=lambda x: x.event_time):
        if e.event_type not in chain:
            chain.append(e.event_type)
    hit = sum(1 for step in STANDARD_CHAIN if step in chain)
    completeness = round(hit / len(STANDARD_CHAIN), 4)

    flags = []
    events = candidate.events
    if "login" in chain and "query" in chain and "export" in chain:
        flags.append("形成登录-查询-导出链条")
    if "copy" in chain or any(e.copy_count > 0 for e in events):
        flags.append("存在本地/USB/共享目录拷贝")
    if "external_send" in chain or any(e.external_send_count > 0 for e in events):
        flags.append("存在外发扩散行为")
    if "delete" in chain or any(e.delete_flag == 1 for e in events):
        flags.append("存在清痕删除行为")
    if "export" in chain and "query" not in chain:
        flags.append("存在未见查询的异常导出跳跃")
    if any(e.compress_flag or e.encrypt_flag for e in events):
        flags.append("存在压缩或加密规避行为")

    return {"behavior_chain": chain, "chain_completeness": completeness, "chain_flags": flags}
