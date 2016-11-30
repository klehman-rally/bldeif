#
# # jv_struct = {
# #               'Views' : [{'View': 'Applebottom', 'include' : '^clownmask', 'AgileCentral_Project' : 'Salamandra'},
# #                          {'View': 'Zebrasteaks', 'exclude' : 'evilstuff,badstuff'}],
# #               'Jobs'  : [{'Job': 'Wendolene Ramsbottom'},
# #                          {'Job': 'Piella Bakewell', 'AgileCentral_Project' : 'Salamandra'}]
# #
# # }
#
#
# jv_struct = {
#         'Jobs': [{'Job': 'Wendolene Ramsbottom', 'AgileCentral_Project': 'Close Shave'},
#                  {'Job': 'Lady Tottington', 'AgileCentral_Project': 'The Curse of the Were-Rabbit'},
#                  {'Job': 'Piella Bakewell', 'AgileCentral_Project': 'A Matter of Loaf and Death'}]
#
#     }
#
#
# box = []
# optional_keys = ['include','exclude','AgileCentral_Project']
# for container, items in jv_struct.items():
#     box.append('%s:' % container)
#     for item in items:
#         item_keys = item.keys()
#         container_item = container[:-1]
#         box.append("    - %s: %s" % (container_item, item[container_item]))
#         for k in optional_keys:
#             if k in item:
#                 box.append("      %s: %s" %(k, item[k]))
#         box.append("")
#
# box = ["        %s" % line for line in box]
# blob = "\n".join(box)
# print(blob)


