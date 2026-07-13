# GitHub Actions Deploy

This site is deployed to Xserver through GitHub Actions using the FTP or FTPS connection configured in the repository secrets.

## Required secrets

Set these in GitHub:

- `FTP_HOST`
- `FTP_USER`
- `FTP_PASS`
- `FTP_REMOTE_DIR`
- `FTP_USE_SSL` is optional. Set it to `true` if your Xserver account uses FTPS.

## How it works

- Push to `main`, or run the workflow manually from the Actions tab.
- The workflow checks out the repository and runs `scripts/deploy-ftp.ps1`.
- The script can also be run locally with `.deploy.env`.

## Local deploy

Create `.deploy.env` from `.deploy.env.example` and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy-ftp.ps1
```
