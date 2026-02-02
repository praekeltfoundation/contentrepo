# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/praekeltfoundation/contentrepo/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                         |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| contentrepo/\_\_init\_\_.py                                                                  |        0 |        0 |    100% |           |
| contentrepo/settings/\_\_init\_\_.py                                                         |        0 |        0 |    100% |           |
| contentrepo/settings/base.py                                                                 |       80 |       10 |     88% |196, 231-233, 235-237, 240-244 |
| contentrepo/settings/dev.py                                                                  |        6 |        0 |    100% |           |
| contentrepo/settings/test.py                                                                 |        9 |        0 |    100% |           |
| contentrepo/urls.py                                                                          |       24 |        4 |     83% |     53-58 |
| home/\_\_init\_\_.py                                                                         |        0 |        0 |    100% |           |
| home/admin.py                                                                                |        5 |        0 |    100% |           |
| home/api.py                                                                                  |      176 |        5 |     97% |91-94, 102 |
| home/api\_v3.py                                                                              |      197 |       12 |     94% |121, 182-186, 247, 249-253, 265-266, 276, 302-305 |
| home/assessment\_import\_export.py                                                           |       19 |        0 |    100% |           |
| home/constants.py                                                                            |        5 |        0 |    100% |           |
| home/content\_import\_export.py                                                              |       21 |        0 |    100% |           |
| home/export\_assessments.py                                                                  |       84 |        1 |     99% |       227 |
| home/export\_content\_pages.py                                                               |      224 |        2 |     99% |  162, 196 |
| home/export\_ordered\_sets.py                                                                |       65 |        1 |     98% |       135 |
| home/export\_whatsapp\_templates.py                                                          |      112 |        4 |     96% |51, 80, 85, 198 |
| home/forms.py                                                                                |       13 |        0 |    100% |           |
| home/import\_assessments.py                                                                  |      249 |        9 |     96% |39, 64, 136-137, 287, 289-292 |
| home/import\_content\_pages.py                                                               |      561 |       12 |     98% |241-242, 354, 402-403, 748, 957-964 |
| home/import\_helpers.py                                                                      |      174 |        8 |     95% |154, 156, 176, 184-188, 230 |
| home/import\_ordered\_content\_sets.py                                                       |      102 |        1 |     99% |       261 |
| home/import\_whatsapp\_templates.py                                                          |      200 |        9 |     96% |32, 55, 220-221, 249, 263, 267, 291, 295 |
| home/management/commands/broken\_links\_clean\_up.py                                         |       31 |        0 |    100% |           |
| home/management/commands/change\_related\_tag\_to\_related\_page.py                          |       26 |        0 |    100% |           |
| home/management/commands/import\_json\_content\_turn.py                                      |       57 |        5 |     91% |     88-92 |
| home/mappers.py                                                                              |        5 |        0 |    100% |           |
| home/migrations/0001\_initial.py                                                             |        4 |        0 |    100% |           |
| home/migrations/0002\_create\_homepage.py                                                    |       19 |        4 |     79% |     39-47 |
| home/migrations/0003\_add\_content\_page.py                                                  |       10 |        0 |    100% |           |
| home/migrations/0004\_auto\_20210329\_0955.py                                                |        7 |        0 |    100% |           |
| home/migrations/0005\_add\_content\_limits.py                                                |        7 |        0 |    100% |           |
| home/migrations/0006\_use\_text\_fields\_message\_content.py                                 |        6 |        0 |    100% |           |
| home/migrations/0007\_add\_struct\_blocks.py                                                 |        9 |        0 |    100% |           |
| home/migrations/0008\_alter\_contentpage\_whatsapp\_body.py                                  |        9 |        0 |    100% |           |
| home/migrations/0009\_add\_index\_page.py                                                    |        5 |        0 |    100% |           |
| home/migrations/0010\_contentpagerating.py                                                   |        5 |        0 |    100% |           |
| home/migrations/0011\_add\_index\_api\_fields.py                                             |        4 |        0 |    100% |           |
| home/migrations/0012\_pageview.py                                                            |        5 |        0 |    100% |           |
| home/migrations/0013\_auto\_20211217\_1132.py                                                |        4 |        0 |    100% |           |
| home/migrations/0014\_contentpage\_is\_whatsapp\_template.py                                 |        4 |        0 |    100% |           |
| home/migrations/0015\_auto\_20220602\_1251.py                                                |        9 |        0 |    100% |           |
| home/migrations/0016\_auto\_20220615\_1123.py                                                |        6 |        0 |    100% |           |
| home/migrations/0017\_contentquickreply\_contenttrigger\_and\_more.py                        |       12 |        0 |    100% |           |
| home/migrations/0018\_pageview\_platform.py                                                  |        4 |        0 |    100% |           |
| home/migrations/0019\_contentpage\_related\_pages.py                                         |        6 |        0 |    100% |           |
| home/migrations/0020\_pageview\_message.py                                                   |        4 |        0 |    100% |           |
| home/migrations/0021\_alter\_contentpage\_tags.py                                            |        5 |        0 |    100% |           |
| home/migrations/0021\_alter\_contentquickreply\_slug\_and\_more.py                           |        4 |        0 |    100% |           |
| home/migrations/0022\_merge\_20220927\_1207.py                                               |        4 |        0 |    100% |           |
| home/migrations/0023\_alter\_contentpage\_whatsapp\_body\_sitesettings.py                    |       10 |        0 |    100% |           |
| home/migrations/0024\_remove\_sitesettings\_content\_variations\_options\_and\_more.py       |        9 |        0 |    100% |           |
| home/migrations/0025\_alter\_contentpage\_whatsapp\_body.py                                  |        9 |        0 |    100% |           |
| home/migrations/0026\_orderedcontentset.py                                                   |        7 |        0 |    100% |           |
| home/migrations/0027\_alter\_orderedcontentset\_options.py                                   |        4 |        0 |    100% |           |
| home/migrations/0028\_alter\_orderedcontentset\_profile\_fields.py                           |        7 |        0 |    100% |           |
| home/migrations/0029\_deduplicate\_slugs.py                                                  |       21 |        0 |    100% |           |
| home/migrations/0030\_contentpage\_whatsapp\_template\_name.py                               |       26 |       12 |     54% |15-19, 23-29 |
| home/migrations/0031\_alter\_contentpagerating\_id\_alter\_contentpagetag\_id\_and\_more.py  |        4 |        0 |    100% |           |
| home/migrations/0032\_alter\_pageview\_timestamp.py                                          |       16 |        5 |     69% | 14, 21-25 |
| home/migrations/0033\_alter\_orderedcontentset\_name\_and\_more.py                           |        6 |        0 |    100% |           |
| home/migrations/0034\_sitesettings\_favicon\_sitesettings\_login\_message\_and\_more.py      |        4 |        0 |    100% |           |
| home/migrations/0035\_contentpage\_embedding.py                                              |        4 |        0 |    100% |           |
| home/migrations/0036\_alter\_contentpage\_messenger\_body\_and\_more.py                      |       10 |        0 |    100% |           |
| home/migrations/0037\_alter\_contentpage\_whatsapp\_body.py                                  |       26 |        5 |     81% |20, 26-28, 32 |
| home/migrations/0038\_alter\_contentpage\_whatsapp\_body.py                                  |       10 |        0 |    100% |           |
| home/migrations/0039\_contentpage\_whatsapp\_template\_category.py                           |        4 |        0 |    100% |           |
| home/migrations/0040\_alter\_contentpage\_whatsapp\_template\_category.py                    |        4 |        0 |    100% |           |
| home/migrations/0041\_alter\_contentpage\_whatsapp\_body.py                                  |       10 |        0 |    100% |           |
| home/migrations/0041\_contentpage\_enable\_sms\_contentpage\_sms\_body\_and\_more.py         |        7 |        0 |    100% |           |
| home/migrations/0041\_contentpage\_whatsapp\_template\_lower\_case\_name.py                  |       23 |       10 |     57% |11-15, 19-25 |
| home/migrations/0042\_merge\_20240122\_0910.py                                               |        4 |        0 |    100% |           |
| home/migrations/0043\_contentpage\_enable\_ussd\_contentpage\_ussd\_body\_and\_more.py       |        7 |        0 |    100% |           |
| home/migrations/0044\_merge\_20240118\_1014.py                                               |        4 |        0 |    100% |           |
| home/migrations/0045\_merge\_20240123\_1102.py                                               |        4 |        0 |    100% |           |
| home/migrations/0046\_alter\_contentpage\_whatsapp\_body.py                                  |       10 |        0 |    100% |           |
| home/migrations/0047\_alter\_contentpage\_messenger\_title\_and\_more.py                     |        4 |        0 |    100% |           |
| home/migrations/0048\_alter\_contentpage\_whatsapp\_body.py                                  |       10 |        0 |    100% |           |
| home/migrations/0049\_assessment\_assessmenttag\_assessment\_tags.py                         |       10 |        0 |    100% |           |
| home/migrations/0049\_orderedcontentset\_expire\_at\_and\_more.py                            |        5 |        0 |    100% |           |
| home/migrations/0050\_orderedcontentset\_locked\_orderedcontentset\_locked\_at\_and\_more.py |        6 |        0 |    100% |           |
| home/migrations/0051\_alter\_contentpage\_sms\_body.py                                       |        7 |        0 |    100% |           |
| home/migrations/0052\_templatecontentquickreply\_templatequickreplycontent\_and\_more.py     |       10 |        0 |    100% |           |
| home/migrations/0053\_merge\_20240404\_1505.py                                               |        4 |        0 |    100% |           |
| home/migrations/0053\_whatsapptemplate\_submission\_name\_and\_more.py                       |        4 |        0 |    100% |           |
| home/migrations/0054\_merge\_20240430\_1022.py                                               |        4 |        0 |    100% |           |
| home/migrations/0055\_alter\_whatsapptemplate\_submission\_name\_and\_more.py                |        4 |        0 |    100% |           |
| home/migrations/0056\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0057\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0058\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0059\_assessment\_version.py                                                 |        4 |        0 |    100% |           |
| home/migrations/0060\_alter\_assessment\_version.py                                          |        4 |        0 |    100% |           |
| home/migrations/0061\_alter\_assessment\_version.py                                          |        4 |        0 |    100% |           |
| home/migrations/0062\_alter\_assessment\_version.py                                          |        4 |        0 |    100% |           |
| home/migrations/0063\_alter\_assessment\_version.py                                          |        4 |        0 |    100% |           |
| home/migrations/0064\_rename\_version\_assessment\_form\_version.py                          |        4 |        0 |    100% |           |
| home/migrations/0065\_rename\_form\_version\_assessment\_version.py                          |        4 |        0 |    100% |           |
| home/migrations/0066\_alter\_assessment\_version.py                                          |        4 |        0 |    100% |           |
| home/migrations/0067\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0068\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0069\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0070\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0071\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0072\_alter\_assessment\_high\_inflection\_and\_more.py                      |        5 |        0 |    100% |           |
| home/migrations/0073\_alter\_assessment\_high\_inflection\_and\_more.py                      |        5 |        0 |    100% |           |
| home/migrations/0074\_alter\_assessment\_high\_inflection.py                                 |        4 |        0 |    100% |           |
| home/migrations/0075\_alter\_assessment\_high\_inflection.py                                 |        4 |        0 |    100% |           |
| home/migrations/0076\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0077\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0078\_alter\_assessment\_high\_inflection\_and\_more.py                      |        4 |        0 |    100% |           |
| home/migrations/0079\_alter\_whatsapptemplate\_message.py                                    |        4 |        0 |    100% |           |
| home/migrations/0080\_assessment\_skip\_high\_result\_page\_and\_more.py                     |        7 |        0 |    100% |           |
| home/migrations/0081\_remove\_contentpage\_embedding.py                                      |        4 |        0 |    100% |           |
| home/migrations/0082\_alter\_contentpage\_whatsapp\_body.py                                  |       10 |        0 |    100% |           |
| home/migrations/0083\_alter\_contentpage\_whatsapp\_body.py                                  |       27 |        3 |     89% |18, 34, 38 |
| home/migrations/0084\_alter\_contentpage\_whatsapp\_body.py                                  |       16 |        5 |     69% |10-12, 17, 21 |
| home/migrations/0085\_orderedcontentset\_locale\_orderedcontentset\_slug.py                  |        6 |        0 |    100% |           |
| home/migrations/0086\_orderedcontentset\_set\_locale\_and\_add\_slug.py                      |       38 |        2 |     95% |    39, 46 |
| home/migrations/0087\_alter\_contentpage\_whatsapp\_body.py                                  |       11 |        0 |    100% |           |
| home/migrations/0088\_alter\_assessment\_questions.py                                        |        6 |        0 |    100% |           |
| home/migrations/0089\_alter\_assessment\_options.py                                          |        4 |        0 |    100% |           |
| home/migrations/0090\_alter\_orderedcontentset\_pages.py                                     |        6 |        0 |    100% |           |
| home/migrations/0091\_alter\_assessment\_slug.py                                             |        4 |        0 |    100% |           |
| home/migrations/0092\_remove\_whatsapptemplate\_quick\_replies\_and\_more.py                 |        8 |        0 |    100% |           |
| home/migrations/0093\_alter\_contentpage\_whatsapp\_body\_and\_more.py                       |       11 |        0 |    100% |           |
| home/migrations/0094\_whatsapptemplate\_unique\_name\_locale.py                              |        4 |        0 |    100% |           |
| home/migrations/0095\_alter\_whatsapptemplate\_submission\_status.py                         |        4 |        0 |    100% |           |
| home/migrations/0096\_migrate\_empty\_submission\_status\_to\_not\_submitted\_yet.py         |       14 |        0 |    100% |           |
| home/migrations/0097\_alter\_whatsapptemplate\_buttons.py                                    |        8 |        0 |    100% |           |
| home/migrations/0098\_whatsapptemplate\_locked\_whatsapptemplate\_locked\_at\_and\_more.py   |        6 |        0 |    100% |           |
| home/migrations/0099\_migrate\_content\_page\_templates\_to\_standalone\_templates.py        |       40 |       26 |     35% |8-13, 22-64 |
| home/migrations/0100\_remove\_contentpage\_is\_whatsapp\_template\_and\_more.py              |       11 |        0 |    100% |           |
| home/migrations/0101\_alter\_whatsapptemplate\_locale.py                                     |        5 |        0 |    100% |           |
| home/migrations/0102\_whatsapptemplate\_slug.py                                              |        4 |        0 |    100% |           |
| home/migrations/0103\_data\_migration\_name\_to\_slug.py                                     |       20 |        8 |     60% |     16-24 |
| home/migrations/0104\_remove\_whatsapptemplate\_unique\_name\_locale\_and\_more.py           |        4 |        0 |    100% |           |
| home/migrations/0105\_alter\_contentpage\_whatsapp\_body.py                                  |       11 |        0 |    100% |           |
| home/migrations/\_\_init\_\_.py                                                              |        0 |        0 |    100% |           |
| home/mixins.py                                                                               |      133 |       15 |     89% |51-53, 57, 61, 102-104, 108, 112, 153-155, 159, 163 |
| home/models.py                                                                               |      626 |       47 |     92% |184, 357, 391, 436, 747, 774-778, 830, 835-839, 869-877, 890, 894, 898, 918-923, 927-932, 950, 970, 1045, 1052, 1059, 1066, 1071, 1080-1082, 1085, 1167, 1218, 1598, 1615, 1622, 1638, 1652, 1673 |
| home/ordered\_content\_import\_export.py                                                     |       17 |        0 |    100% |           |
| home/panels.py                                                                               |       13 |        2 |     85% |     15-16 |
| home/serializers.py                                                                          |      312 |       73 |     77% |22, 25-26, 54, 57, 70, 73, 191, 194-195, 389, 392-393, 397-398, 404-422, 517, 520-521, 524-554, 572-573, 575-576, 578-579, 581-582, 584-585 |
| home/serializers\_v3.py                                                                      |      155 |        7 |     95% |61-64, 94, 101, 132, 189 |
| home/templatetags/\_\_init\_\_.py                                                            |        0 |        0 |    100% |           |
| home/templatetags/container\_tags.py                                                         |        9 |        1 |     89% |        12 |
| home/templatetags/version\_tags.py                                                           |        6 |        0 |    100% |           |
| home/views.py                                                                                |      380 |      158 |     58% |75, 109, 113-114, 181, 219-223, 228-230, 233-271, 276-278, 281-308, 313-314, 317-338, 355-374, 381-394, 408-431, 438-448, 463-483, 490-502, 509-511, 514-533, 550-570, 577-589, 645, 649-654, 678-686 |
| home/wagtail\_hooks.py                                                                       |      144 |        6 |     96% |100, 165-166, 169, 175, 372 |
| home/whatsapp.py                                                                             |      229 |        0 |    100% |           |
| home/whatsapp\_template\_import\_export.py                                                   |       19 |        0 |    100% |           |
| home/xlsx\_helpers.py                                                                        |        5 |        0 |    100% |           |
| **TOTAL**                                                                                    | **5370** |  **472** | **91%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/praekeltfoundation/contentrepo/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/praekeltfoundation/contentrepo/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/praekeltfoundation/contentrepo/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/praekeltfoundation/contentrepo/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fpraekeltfoundation%2Fcontentrepo%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/praekeltfoundation/contentrepo/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.