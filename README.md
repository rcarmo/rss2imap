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
* Feeds can be grouped into folders -- no inbox clutter!
* Generates E-mail headers for threading (so a post that references another will show up as a thread on decent MUAs, and posts from the same feed will be part of the same thread)

# Next Steps:

* Automatic message categorization using Bayesian filtering and NLTK
* Better reference tracking to identify 'hot' items
* Figure out a nice way to do favicons (X-Face is obsolete, and so is X-Image-URL)
