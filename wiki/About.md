### **INTRODUCTION**

Content Management Systems (CMS) have been geared towards content for web pages or rather content that is large in format. However, with the rise of instant messaging (IM), and the various IM platforms, managing content for a service across all platforms has yielded problems for content managers and engineers alike. It has become more expensive to maintain and inefficient. This product aims to solve these problems by creating a content repository that meets the needs of different platforms, content types and languages, giving admins an intuitive journey.

### **BACKGROUND**

Wagtail is a CMS that Praekelt.org has been using since 2015. It is built using Python and Django. A language and web framework we use as well. Wagtail is the CMS of choice for organisations such as National Health Service in the United Kingdom, Nasa, Google Docs and many more. Wagtail is reliable, easily customisable, has built in multiple language support and support of the open source community which results in quick release turnaround time. As an organisation we have used Wagtail for managing web content with many sites and languages in a single instance. With this product we add another layer of complexity by allowing content to be managed for various platforms as well.

### **HEADLESS CMS**
A headless CMS is where the rendering of the content or front-end of the content is decoupled from the creation, deletion and updating of that content. Content is created on the CMS, agnostic of any front end platform it is to be displayed on. A headless CMS makes its content available to platforms via APIs. Wagtail already has headless CMS support.

Instead of having a separate CMS for each of the different platforms an organisation uses such as web, messenger, viber, whatsapp, wechat, freebasics etc, having one CMS that makes a set of content accessible to all these platforms helps solve the following problems:
* Duplication of content - upload content once, edit in one place
* Learning time - editors learn how to use one tool not many
* Engineering time - engineers create and maintain one CMS
* Hosting costs - only one CMS is hosted
* Onboarding - easy onboarding for new platforms, CMS does not change only platform
* Future Proofing - when platforms die or change, content can be repurposed
