# post
cli tool for automating the process of posting files to a website

# usage
`post image.jpg`

  prompt for scale, interactive crop (TODO), remote path (with suggestions), process as necessary and upload

`post file.org` OR

`post file.txt` but contains '-*- mode:org -*-' in first line OR

`post file.txt` but contains heuristic org-mode patterns

  convert to html with emacs, prompt for remote path (with suggestion based on local path), upload

`post other.file`

  prompt for remote path, upload
