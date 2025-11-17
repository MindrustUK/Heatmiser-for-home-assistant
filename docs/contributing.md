---
title: Contributing
nav_order: 12
---

# Development environment

The easiest way to set up a development environment is to follow the [Home Assistant Developer Docs](https://developers.home-assistant.io/) and use their guide to set up a development instance of HA using Docker and VS Code. Then fork this repo, add it to the environment and run the development instance:

1. Follow the instructions here - https://developers.home-assistant.io/docs/development_environment#developing-with-visual-studio-code--devcontainer
1. Go to the [Heatmiser for Home Assistant](https://github.com/MindrustUK/Heatmiser-for-home-assistant) repository and click [Fork](https://github.com/MindrustUK/Heatmiser-for-home-assistant/fork)
1. From the VS Code terminal:
1. add a development folder - `mkdir /workspaces/home-assistant-core/development`
1. Clone your fork of this repository - `git clone https://github.com/<GH USERNAME>/Heatmiser-for-home-assistant.git /workspaces/home-assistant-core/development`. Replace `<GH USERNAME>` with your GitHub username
1. Checkout the dev branch (or other branch if you prefer) - `cd /workspaces/home-assistant-core/development/Heatmiser-for-home-assistant && git checkout dev`
1. Create a symlink so that HA can find the integration code - `ln -s /workspaces/home-assistant-core/development/Heatmiser-for-home-assistant/custom_components/heatmiserneo /workspaces/home-assistant-core/homeassistant/components/heatmiserneo`
1. Restart the Home Assistant instance. The integration should be available now

# Submitting changes

You can run and/or debug the code using VS Code. I would recommend you familiarize yourself with the [Home Assistant Developer Docs](https://developers.home-assistant.io/). Once you are ready to submit a change, the steps are effectively the same as for [contributing](https://developers.home-assistant.io/docs/development_submitting) to Home Assistant itself. Just make sure you commit on the folder where you checked out and submit the [pull request](https://github.com/ocrease/Heatmiser-for-home-assistant/pulls) on the github page for this integration. The process is something like this:

- `cd /workspaces/home-assistant-core/development/Heatmiser-for-home-assistant`
- `git checkout -b some-feature`
- `git add .` (or I prefer `git add -p` to select each change individually)
- `git commit -m "Short description of the change"`
- `git push`

You should now see your changes in your fork of the repository. Create the pull request and add more details of the change. You can also link to an related issue.

# Catching up with reality

You will need to fetch changes to the dev branch if there are any. This could be because a PR has been merged (either yours or someone elses) and you need to have it in your local copy.

You need to set up the main repo as a new upstream remote repository.

- `cd /workspaces/home-assistant-core/development/Heatmiser-for-home-assistant`
- `git remote add upstream https://github.com/MindrustUK/Heatmiser-for-home-assistant.git`

Then to fetch the latest changes from the dev branch run:

- `cd /workspaces/home-assistant-core/development/Heatmiser-for-home-assistant`
- `git checkout dev`
- `git fetch upstream dev`
- `git rebase upstream/dev`

If you have any conflicts you will need to resolve them.

If you have been working on a feature branch and need to incorporate the latest dev into the branch you can also use rebase

- `git checkout some-feature`
- `git rebase dev`

The Home Assistant Developer Docs also include instructions on [how to](https://developers.home-assistant.io/docs/development_catching_up) catch up with reality.

# Other useful commands

The repo uses [pre-commit](https://pre-commit.com/) to check for common errors when you make a commit. One of the steps is to run [Ruff](https://docs.astral.sh/ruff/). These two commands are helpful while developing:

- `cd /workspaces/home-assistant-core/development/Heatmiser-for-home-assistant`
- `ruff check --fix custom_components/heatmiserneo/*.py`
- `ruff format custom_components/heatmiserneo/*.py`

If `pre-commit` makes any changes, you'll need to re-add the changes before you can commit. If it throws any errors, you might need to make the changes manually.

# Making changes to neohubapi

This integration uses the [neohubapi](https://pypi.org/project/neohubapi/). The source is in [gitlab](https://gitlab.com/neohubapi/neohubapi/). If you want to run with a local copy of the api so you can make changes, the steps are very similar to the above. Once you've created a fork:

- `git clone https://gitlab.com/<GITLAB USERNAM>/neohubapi.git /workspaces/home-assistant-core/development`. Replace `<GITLAB USERNAME>` with your GitLab username
- `cd /workspaces/home-assistant-core`
- `pip3 install -e development/neohubapi`
