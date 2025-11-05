ContentRepo works well for storing the tree structure of a browsable menu, or through text search, and storing content for push messages through its Ordered Content Sets.

We also want to be able to store the content for more complicated user interactions, things like onboarding, registration, viewing and editing stored user data, etc. While ContentRepo won't store the complicated business logic and validation for these kinds of flows, it can store the content of the messages for these flows.

This workflow aims to streamline the process of designing flows, managing content, and implementing the flows; while making it easy to link all 3 together.

# Components

This is a suggested workflow for integrating all 3 of:
- Figma for designing the flows and describing the business logic and validation,
- ContentRepo for storing the content of the messages in these flows, and
- whatever flow engine implementing the flows, eg. RapidPro, flow interop, Turn Stacks, using the ContentRepo API to fetch the content.

# Workflow

1. The user flows are created in Figma, with the required business logic and validation described. Each message in the flow has a unique title, which can be used as a slug.
2. The content is in a spreadsheet, and is linked to Figma. This allows the content in Figma to automatically updated whenever there are changes in the spreadsheet. The slug is used to link the row in the spreadsheet to the message block in Figma.
3. This spreadsheet can then be imported into ContentRepo, where the content can be managed. It can also be exported from ContentRepo, to update the content in the Figma flow, when changes are made to the content.
4. The flow engine can access this content through the ContentRepo API. It uses the unique slugs to find the page and content for the specific message. These slugs are hard-coded into the logic of the flow, and allows someone to easily link a specific block in the flow, to a page in ContentRepo, to a row in the spreadsheet, to a message in Figma, which allows for easier debugging and investigation after implementation.