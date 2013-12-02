
(import imaplib [IMAP4 IMAP4_SSL Time2Internaldate])
(import socket [IPPROTO_TCP TCP_NODELAY])
(import datetime [datetime])
(import hashlib [sha1])
(import urlparse [urlparse])

(defn connect-to-server [host port]
	(try
		(let [server 
			(if (= 993 port)
				(IMAP4_SSL host port)
				(IMAP4 host port))]
			(.setsockopt (.sock server) IPPROTO_TCP TCP_NODELAY 1)
			(.login server (.username settings) (.password settings))
			server)
	(catch [e Exception] (print (% "Could not connect to %s:%s: %s" host port e)))))

(defn deliver-message [server folder message]
	(if (== 'NO' (get (.select folder) 0))
		(do
			(.create server folder)
			(.subscribe server folder)))
	(.append server folder "" (Time2Internaldate datetime) message))



;---

(defn best-content-from-entry [entry]
	(let [candidates (get entry 'content' [])]
		(if (get entry 'summary_detail' {})
			(.append candidates (.summary_detail entry)))
		(.strip 
			(first 
				(+ (filter (fn [i] (contains i.type "html")) candidates)
		   	   	   (filter (fn [i] (contains i.type "plain")) candidates))))))

(defn best-id-from-entry [entry]
	(if (and (in "id" entry) (.id entry))
		(if (== (type (.id entry)) (type dict)) 
			(first (.values (.id entry)))
			(.id entry))
		(let [content (best-content-from-entry entry)]
			(cond 
				[content (.hexdigest (sha1 content))]
				[(in "link" entry) (.link entry)]
				[(in "title" entry) (.hexdigest sha1 (.title entry))]))))




(defn best-name-from-entry [result entry overrides]
	(first (+ 
	   (list (get (.feed result) "title" [])
	   (list (get overrides (.url resource)) [])))))


(defn sender-from-feed [result overrides]
	(let [feed (.feed result)
		  name (.lower (get (.feed result) "title" "unknown"))]
		(first (+
			(list (get overrides (.url result)) [])
            (% "%s <%s@%s>" 
            	(get feed "title" "Unnamed Feed") 
            	(.replace name " " "_") 
            	(.netloc (urlparse (.url result))))))))