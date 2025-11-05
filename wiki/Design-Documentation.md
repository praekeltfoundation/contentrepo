Please view the full [Design Documentation Section](https://sites.google.com/praekelt.org/portfolio-projects/platform/content-repo/design-documentation) on the Portfolio Sites pages for more detail

## High-level Content Structure Diagram

  ```mermaid
graph TD;
      Pages --> Homepage
      Homepage -->ContentPageIndex;
      ContentPageIndex -->ContentPage;
      ContentPage -->Web;
      ContentPage -->WhatsApp;
      ContentPage -->SMS;
      ContentPage -->USSD;
      ContentPage -->Viber;
      ContentPage --> Messenger
```

## ContentPage Class Diagram

```mermaid
classDiagram
    ContentPage <|-- Web
    ContentPage <|-- Whatsapp
    ContentPage <|-- SMS
    ContentPage <|-- USSD
    ContentPage <|-- Viber
    ContentPage <|-- Messenger
    Web <|-- WebBody

    Whatsapp <|-- WhatsappTemplateCategory
    Whatsapp <|-- WhatsappBody
    WhatsappBody <|-- "1 or more" WhatsappMessage
    WhatsappMessage <|-- "0 or more" VariableExampleValues
    WhatsappMessage <|-- VariationMessage
    WhatsappMessage <|-- "3" Buttons
    WhatsappMessage <|-- ListItems
    WhatsappMessage <|-- Footer

    VariationMessage <|-- VariationRestriction 
    VariationRestriction <|-- ProfileValue

    Buttons <|-- GotoPage
    Buttons <|-- NextMessage
    
    SMS <|-- "1 or more" SMSBody
   
    USSD <|-- USSDBody

    Messenger <|-- MessengerBody

    Viber <|-- ViberBody

    class SMS{
        +String SmsTitle
        +SMSBody SMSBody
    } 
    class SMSBody{
        String Message
    }
    class USSD{
        +String USSDTitle
        +USSDBody USSDBody
    } 
    class USSDBody{
        +String Message
    }
    class Messenger{
        +String MessengerTitle
        +MessengerBody MessengerBody
    }
    class MessengerBody{
        +Image Image
        +String Message
    }
    class Viber{
        +String ViberTitle
        ViberBody ViberBody
    }
    class ViberBody{
        +Image Image
        +String Message
    }  
    class Web{
        +String Title
        +String Subtitle
        +WebBody WebBody
        +IncludeInFooter()
    }
    class WebBody{
        +String Paragraph
        +Image Image
    }
    class VariationMessage{
    
    }
    class VariationRestriction{
        ProfileValue ProfileValue
    }
    class ListItems{
        +String Title
    }
    class ProfileValue{
        Gender Gender
        Age Age
        Relationship Relationship

    }
    class Buttons{
        NextMessage NextMessage
        GotoPage GotoPage

    }
    class GotoPage{
        String Title
        Page Page
    }
    class NextMessage{
        String Title
    }
    class WhatsappMessage{
        +String Message
        +Image Image
        +Document Document
        +Media Media
        +VariableExampleValues ExampleValues
        +VariationMessage VariationMessage
        +String NextPrompt
        +Buttons Buttons
        +ListItems ListItems
        +Footer Footer

    }
    class Footer{
        String Footer    
    }
    class VariableExampleValues{
        +String ExampleValue
    }
    class WhatsappBody{
        +WhatsappMessage WhatsappMessage
        
    }
    class WhatsappTemplateCategory{
        +String CategoryName
    }
    class Whatsapp{
        +String WhatsappTitle
        +WhatsappTemplateCategory TemplateCategory
        +IsTemplate()
    }
```

## Page Tree Structure

```mermaid
flowchart TD;
   ContentPageIndex2["ContentPageIndex"]
   ContentPage2["ContentPage"]
   
   ContentPageChild2["ContentPage"]
   ContentPageChild3["ContentPage"]
   Pages -- "1 or more, 1 per language" --> Homepage
     
   Homepage  --> ContentPageIndex2
   Homepage  --> ContentPageIndex
   
   ContentPageIndex --> ContentPage2
     
   ContentPage2 --> ContentPageChild2
   ContentPage2 --> ContentPageChild3

   ContentPageChild2 --> ContentPageChild2
   ContentPageChild3 --> ContentPageChild3

```