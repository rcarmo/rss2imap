rss2imap
========

An adaptation of rss2email that uses IMAP directly.

# What does it look like?

Well, with the shipping CSS in `config.py`, it looks like this:

<img src="https://raw.github.com/rcarmo/rss2email/screenshots/mail.app.1.jpg" style="max-width: 100%; height: auto;">

# Main Features:

* E-mail is injected directly via IMAP (so no delays or hassles with spam filters)
* Feeds can be grouped into folders -- no inbox clutter!
* Generates E-mail headers for threading (so a post that references another will show up as a thread on decent MUAs)

# Next Steps:

* Automatic message categorization using Bayesian filtering and NLTK
* Better reference tracking to identify 'hot' items
* Figure out a nice way to do favicons (X-Face is obsolete, and so is X-Image-URL)
