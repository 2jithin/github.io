# Jithin C · Portfolio

A static portfolio for cloud platform engineering, DevSecOps, security, FinOps, and AI-assisted engineering. It uses plain HTML and CSS, so there is no build step or JavaScript dependency.

## Preview locally

From this folder, run `python3 -m http.server 8000` and open `http://localhost:8000/`. Relative links also work when the site is hosted below a repository subdirectory.

## Resume and cover letter

The **Resume** page (`resume.html`) shows readable HTML previews of both documents. Its download buttons point to these original files in `resume/`:

- `Jithin_Azure-AWS_k8sCloudDEVOPS.docx` — downloads with the same filename.
- `cover-letter.pdf` — downloads as `Jithin_C_Cover_Letter.pdf`.

When replacing either document, update its preview text in `resume.html` as well. If a filename changes, update the matching download link and `download` attribute. The HTML preview of the resume corrects the `SAA-Co3` exam-code typo to `SAA-C03`; the original Word document is unchanged.

The files in `images/` are empty placeholders. The site uses CSS and inline SVG for its visual elements.
