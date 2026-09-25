# Jithin C · Portfolio

A static portfolio for cloud platform engineering, DevSecOps, security, FinOps, and AI-assisted engineering. It uses plain HTML and CSS, so there is no build step or JavaScript dependency.

## Preview locally

From this folder, run `python3 -m http.server 8000` and open `http://localhost:8000/`. Relative links also work when the site is hosted below a repository subdirectory.

## Resume and cover letter

The **Resume** page (`resume.html`) shows readable HTML previews of both Word documents and provides download buttons for the originals.

Set up a local Python environment once from the project folder (macOS/Linux):

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On later terminal sessions, run `source .venv/bin/activate` again. After adding or replacing a resume or cover letter in `resume/`, run:

```sh
python scripts/update_resume.py
```

The command chooses the newest resume DOCX and the newest DOCX whose filename contains `cover` or `letter`. It updates both previews and their download links in `resume.html`. You can select specific files when several versions exist:

```sh
python scripts/update_resume.py --resume My-Resume.docx --cover-letter My-Cover-Letter.docx
```

The `.env` file sets the document folder, output page, optional exact filenames, download filenames, and email subject. `RESUME_FILE=auto` and `COVER_LETTER_FILE=auto` keep the upload-and-run workflow. The script uses only Python's standard library; `requirements.txt` currently has no third-party packages to install. The generated `.venv/` folder stays local and is excluded from the site ZIP.

The original Word documents remain in `resume/`. By default, the resume downloads with its source filename and the cover letter downloads as `Jithin_C_Cover_Letter.docx`; both names can be changed in `.env`. Text on Home, About, and Contact is editorial copy; edit those pages if your broader profile details change.

Phone numbers are masked in page previews and on the Contact page. The call link opens a phone dialer; the downloadable Word files retain their original contact details. Email links open the visitor's mail app with a hiring inquiry subject prefilled.

The files in `images/` are empty placeholders. The site uses CSS and inline SVG for its visual elements.
