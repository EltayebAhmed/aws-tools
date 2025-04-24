#!/bin/bash
set -e
mnt-efs-bbc
cd /home/ec2-user/code/gllm
git pull
docker compose up balancer worker0 worker1 worker2 worker3 worker4 worker5 worker6 worker7 -d
cd /home/ec2-user/code/ai-research-ox-llms-as-agents
git checkout semantic_entropy_kw
git pull
docker compose up bbc -d
# docker exec -it ai-research-ox-llms-as-agents-bbc-1 /bin/bash -c /mount/ai-research-ox-llms-as-agents/prompting_kw/math/experiments/STaR/baseline_qwen_2.5_7b/sweep_star_math_base.sh || true
# sudo shutdown now
