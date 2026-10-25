# Seth Peacock — Student Pastor Portfolio

A one-page, mobile-first resume and portfolio site. It's plain HTML, CSS and JavaScript: no build step and nothing to install.

## What's in here

| File | What it is |
|---|---|
| `index.html` | All the words, links and images on the page. **This is the file you'll edit most.** |
| `styles.css` | Colors, fonts, layout and animations. The color palette is at the top (`--purple`, `--coral`, and so on). |
| `script.js` | The menu, scroll animations, number count-up and video player. |
| `resume.pdf` | The file visitors download from "Grab my resume". Currently a placeholder. |
| `images/` | Placeholder pictures to swap for real ones. |
| `videos/` | Where the optional welcome-card preview clip goes. |
| `tests/` | Automated checks (see "Checking your changes" below). |

## Editing your content

Open `index.html` and search for **`EDIT:`**. Every comment like this marks something to change:

```html
<!-- EDIT: your one-line tagline -->
```

Change the text or link right below each one. Things to swap in:

- **Photo:** save a square photo as `images/seth.jpg`, then change `images/seth.svg` to `images/seth.jpg` in `index.html`.
- **App screenshots:** tall phone screenshots work best. Replace `images/app-1.svg` and `images/app-2.svg` the same way.
- **App link:** change `https://example.com/your-app` to your app's real address. It already opens in a new tab.
- **Sermon thumbnails and social post images:** replace the `sermon-*.svg` and `social-*.svg` files the same way.

> **Image file tips:**
> - **Use JPG or PNG.** iPhone photos are often HEIC, which most browsers can't show. In the Photos app, use *File → Export* and choose JPEG.
> - **Name files in all lowercase** (`seth.jpg`, not `Seth.JPG`). Your Mac ignores capital letters in file names, but GitHub doesn't, so a mismatch shows a broken image once it's online. The tests below catch this.

### Videos (welcome video and sermons)

Upload videos to YouTube. "Unlisted" works if you don't want them public on your channel. Then copy the video's ID: the 11 characters after `v=` in the link.

```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
                                └── this part: dQw4w9WgXcQ

https://youtu.be/dQw4w9WgXcQ?si=abc123        (from YouTube's Share button)
                 └── this part: dQw4w9WgXcQ   (stop before the "?")
```

In `index.html`, replace `REPLACE_ME` in `data-video-id="REPLACE_ME"` with that ID. Until you do, tapping the video shows a friendly "Video coming soon!" message.

**Optional preview clip:** the welcome card can play a short, silent loop of you. Make a 5–10 second clip with no sound, keep it under 3 MB, and save it as `videos/hero-preview.mp4`. Until you add it, the card shows `images/hero-poster.svg`. Swap that file for a real photo too, if you like.

### Your resume PDF

Replace `resume.pdf` with a **web version** of your resume (keep the file name `resume.pdf`). This site is public, so leave off anything you don't want everyone to see, like your home address, phone number, or your references' contact details. Also make sure it matches the site: list the same roles, and leave off any role you left off the site.

## Previewing on your computer

In Terminal, from this folder, run:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser. Press `Ctrl+C` in Terminal to stop it.

## Checking your changes

The tests check things like: no phone numbers on the page, every link and image file exists, and your resume dates are right.

```bash
python3 -m unittest discover -s tests -v
```

If a test fails, it names what's wrong. For example, `images/seth.jpg` doesn't exist if you renamed a photo but haven't added the file yet.

## Publishing on GitHub Pages

The easiest way is **GitHub Desktop**, a free app that handles signing in and uploading for you. You won't need the command line.

### First time

1. Create a free account at [github.com](https://github.com).
2. Install [GitHub Desktop](https://desktop.github.com) and sign in with that account.
3. In GitHub Desktop, choose **File → Add Local Repository…** and pick this folder.
4. Check that the branch menu at the top says **main**.
5. Click **Publish repository**. Choose a name, then:
   - **Uncheck "Keep this code private."** Free GitHub Pages only works with public repositories.
   - Name it **`<your-username>.github.io`** for the address `https://<your-username>.github.io/`. Any other name (like `portfolio`) gives you `https://<your-username>.github.io/portfolio/`.
6. On github.com, open your new repository and go to **Settings → Pages**. Under "Build and deployment", choose **Deploy from a branch**, branch **`main`**, folder **`/ (root)`**, then **Save**.
7. Wait a minute or two. Your site's address appears at the top of that Pages screen.

> Don't create the repository on github.com first. If you do, and you tick "Add a README", the upload gets rejected. Let GitHub Desktop create it in step 5.

### Every time you make changes

1. Edit and save your files.
2. Optional: run the tests (see "Checking your changes" above).
3. In GitHub Desktop, your changes show on the left. Type a short summary at the bottom left (like "Add sermon videos") and click **Commit to main**.
4. Click **Push origin** at the top. The live site updates within a minute or two.

### What gets published

Only the site files get published: `index.html`, `styles.css`, `script.js`, `resume.pdf`, `images/` and `videos/`. The `docs/` folder holds private planning notes and is never uploaded, because `.gitignore` excludes it. `_config.yml` keeps `tests/` and this README off the live site.

**Custom domain (optional):** if you buy a domain like `sethpeacock.com`, add it under **Settings → Pages → Custom domain** and follow GitHub's instructions for your domain provider.
