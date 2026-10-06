# Put the Niu Lai demo online

Use GitHub for the repository and Streamlit Community Cloud for the running app.
GitHub Pages serves static sites and cannot run this Python/Streamlit application.
No model account, API key, or live-model configuration is needed for this demo.

## 1. Extract the download

Extract `Niu-Lai-GitHub-Demo.zip`. Open its inner `Niu-Lai-GitHub-Demo` folder.
The files inside that folder are the repository contents. In particular,
`app.py`, `requirements.txt`, and `README.md` should appear at the repository's
top level, alongside `contradiction_workflow/`, `cases/`, `schemas/`, and `tests/`.
Upload the extracted files and folders. Uploading only the ZIP will not produce
a runnable app.

## 2. Create the repository

1. Sign in at [GitHub](https://github.com/new) and create a repository named,
   for example, `niu-lai-research-demo`.
2. For a public reviewer demo, choose **Public**. Leave GitHub's generated
   README, license, and gitignore options off because the package supplies them.
3. On the empty repository page, choose **uploading an existing file**. For a
   repository that already has files, choose **Add file → Upload files**.
4. Drag the contents of the extracted inner folder into the upload area,
   preserving all subfolders, and commit the upload to `main`.
5. Confirm that `app.py` is visible at the top level. Include the supplied
   `.github` folder if you want the automatic checks. Its workflow should appear
   in the repository as `.github/workflows/check-demo.yml`.

The browser supports up to 100 files per upload. If you add more materials later,
use several uploads or GitHub Desktop. Do not upload a local `.venv`, dependency
installation, or generated session runs.

Before a formal public release, fill in the existing project-author and repository
placeholders in `CITATION.cff` and `pyproject.toml`, and the copyright holder in
`LICENSE`. Retain the supplied distinctions between software licensing and
third-party case/theory source rights.

## 3. Run the repository checks

Open **Actions → Check Niu Lai demo**. The included workflow installs Streamlit
and runs the standard-library checks plus two Streamlit AppTest checks. The
interface checks exercise all five steps, the survival review, source/audit
views, separate visitors, and restarting without deleting a prior run.

If there is no workflow, check that the `.github` folder was uploaded. These checks
validate the app; they do not host it. The first successful GitHub run is the
interface validation gate for this package; see `BROWSER_VALIDATION.txt`.

## 4. Deploy the interactive app

Open [Streamlit Community Cloud](https://share.streamlit.io/), sign in, and connect
the GitHub account that can access the repository. Choose **Create app**, then
**Yup, I have an app** if prompted.

| Setting | Value |
| --- | --- |
| Repository | Your GitHub username / `niu-lai-research-demo` |
| Branch | `main`, or the branch where you uploaded the files |
| Main file path | `app.py` |
| Python version, under Advanced settings | `3.12` |
| Secrets | Leave empty; reference replay needs no credentials |
| App URL | Choose an available subdomain, or accept the assigned one |

Click **Deploy**. Community Cloud reads `requirements.txt` and starts the app.
The resulting `streamlit.app` URL is the live demo link. This package has not
already been published to GitHub or deployed to Streamlit.

If you intentionally uploaded the outer folder instead of its contents, the main
file path must include that folder. Keeping the contents at the repository root
is simpler and allows the included GitHub workflow to work as written.

## 5. Check the reviewer experience

Open the live URL in a fresh browser session. Confirm the title says **Niu Lai**,
then follow [the walkthrough](DEMO_WALKTHROUGH.md). Finish the five approval steps,
open the survival review, and download the report and audit ZIP. Open a second
browser session to confirm it starts at Step 1. Test **Start a new demo**.

Add the real live URL to the top of `README.md` and the repository's About/Website
field. In the proposal, provide the live demo URL and the repository URL. For a
fixed submission snapshot, create a tagged release after the checks pass, and
cite that release or commit. The live branch can change over time.

## Run locally instead

From the extracted folder, with Python 3.12 available:

```bash
python -m venv .venv
```

On Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

Each Streamlit session creates a separate directory under `runs/browser/`.
`CONTRADICTION_RUN_DIR`, if set, changes that parent directory. A fresh page
session or **Start a new demo** uses a new directory. Records remain append-only
within a run; restarting does not delete earlier runs. Hosted local files are
temporary, so download the records you want to retain. This demo has no durable
account-based project storage.

## Official instructions

- [Deploy a Streamlit app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Upload files to GitHub](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)
- [GitHub Pages and its static hosting limits](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [Streamlit interface testing](https://docs.streamlit.io/develop/concepts/app-testing/get-started)
