# Aurora DSQL Implementation Examples

This file contains DSQL integration code examples; only load this when actively implementing database code.

For language-specific framework selection, recommendations, and examples see [language.md](./language.md).

For developer rules, see [development-guide.md](./development-guide.md).

For additional samples, including in alternative language and driver support, refer to the official
[aurora-dsql-samples](https://github.com/aws-samples/aurora-dsql-samples).

---

## Detailed Examples

Load the relevant file for the specific implementation pattern you need:

- **[examples/connection.md](examples/connection.md)** — Ad-hoc queries with psql, connection management, token generation
- **[examples/schema.md](examples/schema.md)** — Table creation, index creation, column modifications
- **[examples/data-operations.md](examples/data-operations.md)** — Basic CRUD, batch processing, concurrent inserts
- **[examples/migrations.md](examples/migrations.md)** — Migration execution patterns
- **[examples/patterns.md](examples/patterns.md)** — Multi-tenant isolation, referential integrity, sequences, data serialization

## References

- **Development Guide:** [development-guide.md](./development-guide.md)
- **Language Guide:** [language.md](./language.md)
- **Onboarding Guide:** [onboarding.md](./onboarding.md)
- **AWS Documentation:** [DSQL User Guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- **Sample Code:** [aurora-dsql-samples](https://github.com/aws-samples/aurora-dsql-samples)
