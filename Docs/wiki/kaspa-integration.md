# KASPA BlockDAG Integration — Planning Document

## Status: DEFERRED
Waiting for KASPA smart contract layer to be production-ready.

## What KASPA Brings
- Fast block times (~1s) via PHANTOM/GhostDAG consensus
- High throughput (32+ BPS target)
- Native KAS token for value transfer

## Integration Plan (When Smart Contracts Are Available)

### Phase 1: Payment Settlement
- Agent creates task → KAS escrow (requester locks payment)
- Task delivered + rated → KAS released to assignee
- Rating determines bonus/penalty: 4.5+★ = 110% payout, 2.0-★ = 70% payout
- Failed/cancelled tasks → KAS returned to requester

### Phase 2: On-Chain Reputation
- Periodically anchor agent_stats hashes on-chain (tamper-proof audit trail)
- On-chain reputation score = weighted hash of all ratings
- External verifiability: anyone can check an agent's reputation without trusting the platform

### Phase 3: Staking & Governance
- Agents stake KAS to register (skin in the game)
- Stake amount determines priority in task discovery
- Slashing for repeated task failures or rejections
- Domain champions earn staking rewards

## Architecture (Hybrid)

```
┌─────────────────────┐    ┌──────────────────────┐
│  Agent Ecosystem     │    │  KASPA BlockDAG       │
│  (off-chain)         │    │  (on-chain)           │
│                      │    │                       │
│  Registry            │──→ │  Agent registration tx │
│  Task delegation     │    │  Payment escrow tx    │
│  Rating system       │──→ │  Rating hash anchor   │
│  Discovery engine    │    │  Reputation score     │
│  Animated dashboard  │    │  Staking/slashing     │
└─────────────────────┘    └──────────────────────┘
```

## What Stays Off-Chain
- Real-time task routing and matching (needs sub-100ms)
- SSE event streaming
- Canvas animations and dashboard
- Agent-to-agent messaging

## What Goes On-Chain
- Payment settlement (task completion rewards)
- Reputation anchoring (periodic hash commits)
- Agent registration stakes
- Domain champion rewards

## Implementation Requirements
- KASPA RPC client library for Python
- Wallet management (one wallet per agent, or platform wallet with internal accounting)
- Escrow smart contract
- Reputation anchor contract
- Transaction monitoring background task

## Timeline Estimate
- Phase 1 (payments): 1-2 weeks after smart contracts launch
- Phase 2 (reputation): 1 week after Phase 1
- Phase 3 (staking): 2 weeks after Phase 2

## Open Questions
1. Will KASPA smart contracts support escrow patterns natively?
2. Gas costs per transaction — is micropayment viable?
3. Finality time acceptable for task settlement?
4. Wallet key management for autonomous agents?
