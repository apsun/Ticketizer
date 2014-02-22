What is Ticketizer? Why, it's only the best to happen to
12306.cn since, well, 12306.cn! To be specific, it's a
library (written in Python!) that abstracts away most of
the underlying web API, leaving only an efficient and
simple API for client code to call.

Ticketizer is driven by the philosophy that you shouldn't
have to jump through hoops to get where you want. Under
no circumstances should clients have to step through dozens
of web requests just to query the number of tickets remaining.

There are two major components to Ticketizer: a core
("business logic") component, which is responsible for
abstracting away all web requests, and a UI component,
which takes the raw data from the core component and
exposes it to the user. The core layer has been designed
to allow for interchangeable UI layers, which means
you can use the core layer from both CLI and GUI alike.