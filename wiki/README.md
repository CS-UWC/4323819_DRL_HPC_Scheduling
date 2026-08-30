# GitHub Wiki source mirror

These Markdown files are the reviewable backup of the project Wiki owned by **JCheney20**.

- Web: <https://github.com/JCheney20/DRL_HPC_Scheduling/wiki>
- Wiki Git remote: `git@github.com:JCheney20/DRL_HPC_Scheduling.wiki.git`
- Repository: <https://github.com/JCheney20/DRL_HPC_Scheduling>

The Wiki remote is not initialized yet. The owner must enable Wiki and create the first `Home` page on GitHub once. Then publish this directory to the separate Wiki repository:

```bash
ssh -T git@github.com
git clone git@github.com:JCheney20/DRL_HPC_Scheduling.wiki.git ../DRL_HPC_Scheduling.wiki
rsync -a --delete --exclude='.git/' --exclude='README.md' wiki/ ../DRL_HPC_Scheduling.wiki/
cd ../DRL_HPC_Scheduling.wiki
git add .
git commit -m "Publish reproducibility guides"
git push
```

Review changes here before copying them. Protocols and machine-readable contracts remain authoritative under [`docs/`](../docs/); Wiki pages link to them instead of copying them.
