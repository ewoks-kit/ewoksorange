"""Reading HDF5 files, whichever process is writing them.

One module per access regime: `live` for a file another process may write,
`owned` for a file this process writes, `links` for the files external links
point at. See the HDF5 access explanation in the documentation.
"""
