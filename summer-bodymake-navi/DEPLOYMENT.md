# GitHub Actions Deploy

This site is deployed to XServer Static through GitHub Actions using the FTPS connection configured in the repository secrets.

## Required secrets

Set these in GitHub:

- `FTP_HOST`: XServer Static FTP server name, for example `staticXX.xserver.jp`
- `FTP_USER`: XServer Static FTP account name
- `FTP_PASS`: XServer Static FTP password
- `FTP_REMOTE_DIR`: normally `/public_html`
- `FTP_USE_SSL`: normally `true` for XServer Static FTPS

## How it works

- Push to `main`, or run the workflow manually from the Actions tab.
- The workflow checks out the repository and runs `scripts/deploy-ftp.ps1`.
- The script can also be run locally with `.deploy.env`.

## Local deploy

Create `.deploy.env` from `.deploy.env.example` and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-ftp.ps1
```
