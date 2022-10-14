## Author
GV | Swiss Staking ([@swiss_staking](https://twitter.com/swiss_staking))
## Intro 
The [Diffusion](https://www.mintscan.io/evmos/proposals/64) incentives will start soon. As you might know, some incentivized pools require to bridge assets from Ethereum via Axelar/Gravity to Evmos. Once they are bridged to Evmos, you must convert them (on the [asset page](https://app.evmos.org/assets) of Evmos) from IBC-coins to ERC-20 tokens. This requires a fee of about ~0.3 Evmos. New ecosystem participants won’t own any Evmos at this time, so it is crucial to implement a faucet who funds them. This situation is only temporary, as the team will implement an auto-conversion on protocol level in the near future. Until then, it’s our job to onboard new participants with ease to unleash the full potential of the DeFi revival on Evmos.
## Architecture 
The bot will be available on the Discord faucet channel of Evmos. To minimize any gaming of the faucet we will implement a cooldown period, a minimum number of assets that must be deposited on the [asset page](https://app.evmos.org/assets) and further on-chain checks. The bot's wallet will be funded by the multisig on a bi-weekly basis (or if the balance gets close to zero). Furthermore, we might fund additional hot-wallets for faucet purposes.
## Funds 
Onboarding 20,000 users is a likely scenario thus we ask for 6,000 Evmos to be used for dust. Unused Evmos will be returned within 6 months. Code refactoring, integration and management of the bot is volunteer effort. 
## Gnosis Safe (Multisig)
Address: evmos1clc75pp4sqx4kus3r79uq88d08vc25dkq6483h, 2/4 confirmation: 
- GV | Swiss Staking 
- Dev_D (mod)
- Benny (mod / gov ws)
- Sigmung | Qubelabs
## Commonwealth
This proposal was discussed on [Commonwealth](https://commonwealth.im/evmos/discussion/7208-faucet-for-defi-kickoff)


