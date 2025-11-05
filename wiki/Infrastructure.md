# Infrastructure and Deployment

## Infrastructure

```mermaid
flowchart TB
    A([User])-->B([Webpage])
    A-->D([Messenger])
    A-->E([Viber])
    A-->C([Whatsapp])
    C<-->F([Turn.io])
    F<-->G([RapidPro])
    D<-->G
    E<-->G
    F-->H[(BigQuery)]
    H-->I([ETL Scripts])
    G<-- API interaction -->J([Contentrepo])
    B<-- API interaction -->J
    I-->G
    style A fill:#f9f,stroke:#333,stroke-width:4px,color:#fff
    style B fill:#f1b24f,stroke:#333,stroke-width:4px,color:#fff
    style D fill:#4267B2,stroke:#333,stroke-width:4px,color:#fff
    style E fill:#7360F2,stroke:#333,stroke-width:4px,color:#fff
    style C fill:#25D366,stroke:#333,stroke-width:4px,color:#fff
    style F fill:#00b6bf,stroke:#333,stroke-width:4px,color:#fff
    style G fill:#0d6597,stroke:#333,stroke-width:4px,color:#fff
    style H fill:#4386fa,stroke:#333,stroke-width:4px,color:#fff
    style I stroke:#333,stroke-width:4px,color:#fff
    style J fill:#EE3016,stroke:#333,stroke-width:4px,color:#fff
```

Contentrepo is used to manage all content, without concern for the frontend. RapidPro and/or Turn.io will be needed to manage the flows and user journeys. The Contentrepo content can be accessed via the API.

## Deploy

Contentrepo is deployed using Kubernetes. When a commit on the Contentrepo repo is tagged in Github, an image is pushed to Dockerhub. That Docker image can be used to create a container to run Contentrepo for your project.
