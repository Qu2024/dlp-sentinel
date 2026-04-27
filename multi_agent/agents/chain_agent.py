from .base_agent import BaseAgent


class ChainAgent(BaseAgent):
    name = "行为链重构Agent"
    STANDARD_CHAIN = ["login", "query", "export", "copy", "external_send", "delete"]

    def _build_chain(self, events):
        chain = []
        for e in sorted(events, key=lambda x: x.event_time):
            if e.event_type not in chain:
                chain.append(e.event_type)
        return chain

    def _completeness(self, chain):
        hit = sum(1 for step in self.STANDARD_CHAIN if step in chain)
        return round(hit / len(self.STANDARD_CHAIN), 4)

    def _flags(self, chain, events):
        flags = []
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
        return flags

    def run(self, candidates):
        results = {}
        for c in candidates:
            chain = self._build_chain(c.events)
            results[c.candidate_event_id] = {
                "behavior_chain": chain,
                "chain_completeness": self._completeness(chain),
                "chain_flags": self._flags(chain, c.events),
            }
            c.chain_result = results[c.candidate_event_id]

        trace = self.trace(
            {"candidate_count": len(candidates)},
            {
                "chain_analyzed_count": len(results),
                "high_completeness_count": sum(1 for r in results.values() if r["chain_completeness"] >= 0.6),
            },
        )
        return results, trace
