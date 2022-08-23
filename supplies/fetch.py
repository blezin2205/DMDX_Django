# docs = db.collection(u'orders').stream()
# for index, doc in enumerate(docs):
#
#     ordId = doc.to_dict()['orderId']
#     order = Order.objects.get(id=ordId)
#
#     supp_docs = db.collection(u'orders').document(doc.id).collection(u'supplies').stream()
#     for sup in supp_docs:
#         name = sup.to_dict()['name']
#
#         try:
#             device = sup.to_dict()['device']
#         except:
#             device = None
#
#         try:
#             supplyLot = sup.to_dict()['supplyLot']
#         except:
#             supplyLot = None
#
#         expiredDate = sup.to_dict()['expiredDate']
#         date_created = sup.to_dict()['dateCreated']
#         countinorder = sup.to_dict()['countInOrder']
#
#         if countinorder < 0:
#             countinorder = 0
#
#         try:
#             suppp = Supply.objects.get(firebase_id=sup.id)
#
#             supInOrder = SupplyInOrder(count_in_order=countinorder, general_supply=suppp.general_supply,
#                                        supply_for_order=order, lot=supplyLot, date_created=date_created,
#                                        date_expired=expiredDate)
#             supInOrder.save()
#         except:
#
#             try:
#                 category = Category.objects.get(name=device)
#             except Category.DoesNotExist:
#                 category = None
#
#             try:
#                 genSup = GeneralSupply.objects.get(name=name)
#             except:
#                 genSup = GeneralSupply(name=name, category=category)
#                 genSup.save()
#
#             supInOrder = SupplyInOrder(count_in_order=countinorder, generalSupply=genSup, supply_for_order=order,
#                                        lot=supplyLot, date_created=date_created, date_expired=expiredDate)
#             supInOrder.save()
#
#
#
#
#
#
#
#
#
# // SUPPLY FETCH
#
# docs = db.collection(u'supplies').stream()
# for index, doc in enumerate(docs):
#     supplyname = ''
#     supplyname = doc.to_dict()['name']
#     denName = ''
#     denName = doc.to_dict()['device']
#     count = doc.to_dict()['count']
#     dateCreated = doc.to_dict()['dateCreated']
#     dateExpired = doc.to_dict()['expiredDate']
#     lot = doc.to_dict()['supplyLot']
#     firebaseId = doc.id
#
#     dev = denName.strip()
#
#     try:
#         category = Category.objects.get(name=dev)
#     except:
#         category = None
#
#     genName = supplyname.strip()
#
#     try:
#         genSup = GeneralSupply.objects.get(name=genName)
#
#     except:
#         genSup = None
#
#     if count < 0:
#         count = 0
#
#     supply = Supply(firebase_id=firebaseId, name=genName, general_supply=genSup, category=category, supplyLot=lot,
#                     count=count, dateCreated=dateCreated, expiredDate=dateExpired)
#     supply.save()