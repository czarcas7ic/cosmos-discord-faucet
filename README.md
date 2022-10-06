# osmosis-discord-faucet
Discord faucet bot for Osmosis  


<details>
  <summary>List of available commands:</summary>

1. Request coins through the faucet  
`$request osmo1a5zxevtdwhy4ddj662rl8xqyqsnrdmv7007g32`

Transaction status explanation:  
✅ - mean bot send transaction to your address

2. Displays the current status of the node where faucet is running  
`$faucet_status`

3. Show faucet address  
`$faucet_address`

4. Show transaction information for a specific transaction ID  
`$tx_info 5C501EA776F66ADB6A5A3C13D876382FFE431A461E1AA7AD7A19D70C6B765A97`

5. Show address balance  
`$balance osmo1a5zxevtdwhy4ddj662rl8xqyqsnrdmv7007g32`  

</details>  


## Requirements
- python3.6+  
- Cosmos REST server (default port 1317)  
- Cosmos RPC server  (default port 26657)

## How to install  
1. Run command below  
```bash
apt update \
&& apt install -y python3-pip python3-venv git tmux \
&& git clone https://github.com/czarcas7ic/osmosis-discord-faucet.git \
&& cd evmos-discord-faucet \
&& python3 -m venv venv \
&& source venv/bin/activate \
&& pip3 install -r requirements.txt
```
2. [Create Discord token](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token)  
3. Fill in config.ini  
4. Invite the bot to your channel  
5. Start Osmosis Daemon and sync the node  


## How to run  
Start faucet bot  
```
tmux new -s discord_faucet_bot -d cd ~/osmosis-discord-faucet && source venv/bin/activate && python3 discord_faucet_bot.py
```  
  
### Alternatively, the bot can be run through systemd:  
- If necessary, change the username and the path to the script folder in `discord-faucet-bot.service`  

- Start the service  
```
ln -s $HOME/osmosis-discord-faucet/osmosis-faucet-bot.service /etc/systemd/system/ \
&& systemctl daemon-reload \
&& systemctl enable osmosis-faucet-bot.service \
&& systemctl start osmosis-faucet-bot.service \
&& systemctl status osmosis-faucet-bot.service
```  

