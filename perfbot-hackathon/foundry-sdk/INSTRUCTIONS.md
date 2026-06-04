# VS Code for the Web - Microsoft Foundry

We've generated a simple development environment for you to play with sample code to create and run the agent that you built in the Microsoft Foundry playground.

The Microsoft Foundry extension provides tools to help you build, test, and deploy AI models and AI Applications directly from VS Code. It offers simplified operations for interacting with your models, agents, and threads without leaving your development environment. Click on the Microsoft Foundry Icon on the left to see more.

Follow the instructions below to get started!

## Open the terminal

Press ``Ctrl-` `` &nbsp; to open a terminal window.

## Run your agent locally

To run the agent that you created in AI Foundry, and view the output in the terminal run the following command:

```bash
python run_agent.py
```

## Update your agent configuration

In the left hand activity bar:

- Open the Microsoft Foundry tab in the navigation bar
- Under "Resources", expand the "Agents" section and click on the corresponding agent name
- Click "Open YAML File"
- Make any changes to the agent definition
- Update the agent in Microsoft Foundry

## Add, provision and deploy web app that uses the agent

To add a web app that uses your agent, run the next command. When asked what you would like to do with the files, we suggest selecting `Overwrite with versions from template`.

```bash
azd init -t https://github.com/Azure-Samples/get-started-with-ai-agents
```

You can provision and deploy this web app using:

```bash
azd up
```

To delete the web app and stop incurring any charges, run:

```bash
azd down
```
