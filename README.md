rss2imap
========

An adaptation of rss2email that uses IMAP directly.

# What does it look like?

Well, with the shipping CSS in `config.py`, it looks like this:

<img src="https://raw.github.com/rcarmo/rss2email/screenshots/mail.app.1.jpg" style="max-width: 100%; height: auto;">

## What about mobile?

Well, it works fine with the Gmail app on both Android and iOS, as well as the native IMAP clients:

<img src="https://raw.github.com/rcarmo/rss2email/screenshots/gmail.ios.1.jpg" width="25%"> <img src="https://raw.github.com/rcarmo/rss2email/screenshots/mail.ios.1.jpg" width="25%"> <img src="https://raw.github.com/rcarmo/rss2email/screenshots/gmail.android.1.jpg" width="25%"> <img src="https://raw.github.com/rcarmo/rss2email/screenshots/mail.android.1.jpg" width="25%">

As long as you sync, all the text will be available off-line (images are cached at the whim of the MUA).

The Gmail app ignores CSS and may have weird behaviors with long bits of text, though.

# Main Features:

* E-mail is injected directly via IMAP (so no delays or hassles with spam filters)
* Feeds can be grouped into IMAP folders -- no inbox clutter!
* Generates E-mail headers for threading, so a post that references another post (or that includes the same link) will show up as a thread on decent MUAs. Also, posts from the same feed will be part of the same thread)
* Can (optionally) include images inline (as `data:` URIs for now -- which only works properly on iOS/Mac -- soon as MIME attachments)
* Can (optionally) remove read (but not flagged) items automatically

# Next Steps:

* Test nested folders (am only using single folders, not a nested hierarchy, so this might break)
* Automatic message categorization using Bayesian filtering and NLTK
* Better reference tracking to identify 'hot' items
* Figure out a nice way to do favicons (X-Face is obsolete, and so is X-Image-URL)
* Refactor this as a multi-threaded app with a SQLite feed store

Be aware that this works and is easy to hack, but uses old Python idioms and could do with some refactoring (PEP-8 zealots are sure to cringe as they read through the code).
