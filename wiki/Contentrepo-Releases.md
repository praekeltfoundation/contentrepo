# QA Environment

### Merge builds
Process to merge to main branch
* Create pull request(PR)
* Add ticket purpose description
* Every PR require to be approved by someone before it can be merged
* Once the PR is approved then you can merge to the main branch
* Use merge commit hash on this repo cluster-infra-prk/prk-prd-aws-za/apps/content-repo-api-qa/ytt-django.yaml by updating the hash key on container_image.
* Run this command to regenerate and apply the changes `kustom-tool -c prk-prd-aws-za/kustom.yaml regenerate`
* Commit and push the two updated files.
* Create a PR 
* Merge it once it has been approved

### How we can test
### Multiple QA instances

# Prod Environment

### Release Tags
### How they're used for prod
### When we do release tags
### Updating release notes
### Updating version number
### Creating release tag