# Introduction
Forms are used to collect information from users, by asking them a series of questions. It handles validation of user responses, and storing their responses. You can think of it as similar to Google Forms.

The CMS is responsible for creating, storing, managing, and maintaining the content and metadata of the forms, but is not responsible for asking questions, validating responses, and storing results. That is the responsibility of the channel-specific implementations.

This functionality started as a [proposal](https://docs.google.com/document/d/1GcXOvadYl0QifIz0kUzVKyjqIkOuo3zz1AgcUDBro9U/edit?tab=t.0#heading=h.1fz8gjbpj6b)

Forms are currently accessible in the CMS's content admin interface, under the "Assessments" heading. There forms can be viewed and edited, as well as bulk imported and exported.

# Form fields
## Identifiers
These fields are used to identify this Form.
| Name | Description |
| ---- | ----------- |
| Title | This is the name of the Form that might be shown to the user. It is a text field that can contain any characters, with a maximum length of 255 characters. This field is required. |
| Slug | The slug, combined with the locale, form the unique identifier for the Form. This means that for form translations, they should have the same slug, but a different locale. Slugs can only contain lowercase or uppercase letters, numbers, underscores, or hyphens, and have a maximum length of 255. This field is required. |
| Version | While wagtail gives us revisions and edit history, the version field is to allow us to manage changes to the data we get from user responses. The version field is a text field with a maximum length of 200 characters. It is managed through careful use of the CMS's moderation features, and through internal process. The idea here is that changes to wording or corrections to grammar and spelling will create a new revision, but not necessarily a new version. While significant changes to questions and answers, that would require alternate interpretations to the user response data, will require a version change. This field is optional. |
| Locale |This is the locale that the questions and answers are written in. It is used if we have translations of a Form, that we select the form with the locale matching the user. It is required. |
| Tags | Tags are used to organize Forms. They can also be used to customize which Form to send to a user, based on matching the user's profile to the tags on the forms. It is not required. |

## Results
These fields control what happens after the user has completed all of the questions on the Form.
| Name | Description |
| ---- | ----------- |
| High result page | This is the content page that we show the user if their answers categorize them as high risk. It is optional. |
|  High inflection | This is the percentage score that if the user scores at or above this amount, they are considered high risk, and should be shown the high result page. It is optional. |
| Medium result page | This is the content page that we show the user if their answers categorize them as medium risk. It is optional. |
| Medium inflection | This is the percentage score that if the user scores at or above this amount, but lower than the high inflection, they are considered medium risk, and should be shown the medium result page. Any score below this inflection is considered low risk. It is optional. |
| Low result page | This is the content page that we show the user if their answers categorize them as low risk. It is optional. |
| Skip threshold | If the amount of questions that the user skips is equal to or greater than this amount, then they will be shown the skip high result page instead of the result page related to their score.|
| Skip high result page | The content page that we show the user if they skip enough questions to be at or above the skip threshold. This is optional. |

## Questions
These fields all have to do with the questions that we ask the user as part of this form.
### Generic error
This is the error message shown to the user if their response doesn't comply with the validation for any of the questions. The validation depends on the question type. Each question can also specify a specific error message for that question, in which case this generic error is only used if a specific error for the question is not specified. It is required.

### Questions
This is a list of all the questions that we would want to ask the user. There are a number of different question types, which have different options which affect the validation.

All questions have the following fields:
| Name | Description |
| ---- | ----------- |
| Question | the text for the question that we want to ask the user |
| Explainer | the text to send to the user if they want to know why we are asking them this question |
| Semantic ID | This is an ID that is per-form unique. It is used to uniquely identify the question within the current form. It is the same across locales, and so it should not be translated, and can be used to know which question this is independent of the question text. It is used when analysing the data, and displaying the results on dashboards. By convention, we always have the question semantic ID be in [snake_case](https://en.wikipedia.org/wiki/Snake_case), e.g. `diet_changes` |

#### Categorical question
This is used if we want the user to select a single response from a predefined set of possible answers.

It will validate that the user's response is one of the options in the set of possible answers.

It adds the following fields to the base fields:
| Name | Description |
| ---- | ----------- |
| Error | The error message to display to the user if they response with something that is not one of the options |
| Answers | The list of possible answers |

##### Answer
Each answer represents one item of the list of possible answers for a question. They contain the following fields:
| Name | Description |
| ---- | ----------- |
| Answer | This is the text that is shown to the user for this answer choice |
| Score | This is the amount that is added to the user's total score for this form if they choose this choice |
| Semantic ID | This is an ID that is per-question unique. It is used to identify this answer within the current question. It is the same across locales, and so it should not be translated, and it is used to know which answer this is independent of the answer text that is shown to the user. It is used when analysing the data, and displaying the results on dashboards. By convention, we use a human-readable format, e.g. `Strongly agree`|

#### Multi-select question
This is similar to the Categorical question, and has the same fields, but allows the user to select more than one answer as their response to the question.

#### Age question
This allows the user to response with their age, in years. This is a deprecated question type that will soon be removed, please use the Integer question type instead.

#### Free Text question
This allows the user to respond with any text that they like. As such, it has no validation and no error message. It doesn't add any additional fields to the base fields.

#### Integer question
This allows the user to response with an integer number, and validates that it is within a certain range. It has the following fields:
| Name | Description |
| ---- | ----------- |
| Min | The minimum value that the user can answer in response to this question |
| Max | The maximum value that the user can answer in response to this question |
| Error | The error message to send to the user if they respond with a non-integer, or an integer that is outside of the specified range |

#### Year of birth question
This allows the user to enter an integer representing the year of birth. It ensures that the year is between the current year and 120 years ago.