# Diagnostic branch-pr 2026-09-03T13:49:35Z

## gh pr create (GraphQL)
```
pull request create failed: GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)
```
## gh api REST
```
gh: GitHub Actions is not permitted to create or approve pull requests. (HTTP 403)
```
Piste : Settings -> Actions -> General -> Workflow permissions ->
'Allow GitHub Actions to create and approve pull requests'.
