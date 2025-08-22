# Test data layout

- books/: large inputs that are user-provided and NOT committed
  - Each book has its own folder (e.g., lord_of_the_flies/)
- outputs/: expected outputs or hashes for small synthetic fixtures that we can commit

## Notes

- Do not commit copyrighted PDFs. Place them locally under tests/data/books/.
- Add your own files; .gitignore prevents accidental commits.
