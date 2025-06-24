# Moogla Web Interface

This folder contains a minimal web interface for interacting with a running
Moogla server. The UI is styled using [Tailwind CSS](https://tailwindcss.com).

A reference design is available in Figma. You can duplicate it from:

```
https://www.figma.com/community/file/13978200592474809/Moogla-UI-Demo
```

To use the interface, start the Moogla server and open
`http://localhost:11434/app` in your browser. Messages are sent to the
`/v1/chat/completions` endpoint and replies are displayed on the page.
