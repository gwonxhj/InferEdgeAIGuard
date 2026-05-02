# Portfolio Demo Cases

This directory documents the Phase 6 AIGuard portfolio demo bundle.

The bundle is generated from the existing local fixtures instead of requiring a
service, database, queue, or Lab import:

```bash
python -m inferedge_aiguard.cli portfolio-demo \
  --save-json reports/portfolio_demo/aiguard_portfolio_demo.json \
  --save-md reports/portfolio_demo/aiguard_portfolio_demo.md
```

Demo cases:

| Case | Expected guard verdict | Purpose |
| --- | --- | --- |
| normal output quality | `pass` | Shows stable bbox/score evidence. |
| latency improvement with bbox collapse | `blocked` | Shows speedup is not enough when bbox quality collapses. |
| confidence score saturation | `blocked` | Shows score distribution evidence for quantization/postprocess risk. |
| temporal instability | `review_required` | Shows frame-level instability evidence without a tracker dependency. |

AIGuard remains an optional deterministic evidence provider. InferEdgeLab remains
the final deployment decision owner.
