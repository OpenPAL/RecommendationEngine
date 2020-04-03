from z3 import *
from maneuverRecomadEngine.exactsolvers.ManuverSolver import ManuverSolver
import time

class Z3_Solver_Parent(ManuverSolver):#ManeuverProblem):

    def _initSolver(self):
        """
        Initializes the solver
        :return: None
        """
        if self.solverTypeOptimize:
            self.solver = Optimize()
        else:
            self.solver = Solver()
            self.solver.set(unsat_core=True)
            self.labelIdx = 0
            self.labelIdx_oneToOne = 0
            self.labelIdx_offer = 0
            self.labelIdx_conflict = 0

        self.vmIds_for_fixedComponents = set()
        self._defineVariablesAndConstraints()

    def _defineVariablesAndConstraints(self):
        # VM usage vector vm in {0, 1}, k = 1..M; vm_k = 1 if at least one component is assigned to vm_k.
        self.vm = {}
        # Assignment matrix a_{alpha,k}: 1 if component alpha is on machine k, 0 otherwise
        self.a = {}
        # VMType  - type of a leased VM
        self.VMType = {}

    def _symmetry_breaking(self):
        max_id = -1
        for vmid in self.vmIds_for_fixedComponents:
            if max_id < vmid:
                max_id = vmid
        self.RestrictionPriceOrder(max_id+1, self.nrVM)


        #print("vmIds_for_fixedComponents: ", self.vmIds_for_fixedComponents, max_id)
        # VMs of same type (price) are ordered by components load, and for same load by lex
        if self.sb_vms_price_order_by_components_number_order_lex:
            for j in range(max_id + 1, self.nrVM - 1):
                self.solver.add(Implies(self.PriceProv[j] == self.PriceProv[j+1],
                                        sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)])
                                        >= sum([self.a[i + j + 1] for i in range(0, len(self.a), self.nrVM)])))
                for i in range(0, self.nrComp):
                    l = [self.a[u * self.nrVM + j] == self.a[u * self.nrVM + j + 1] for u in range(0, i)]
                    l.extend([self.PriceProv[j] == self.PriceProv[j+1],
                                 sum([self.a[h + j] for h in range(0, len(self.a), self.nrVM)]) ==
                                 sum([self.a[h + j + 1] for h in range(0, len(self.a), self.nrVM)])])
                    self.solver.add(Implies(And(l), self.a[i * self.nrVM + j] >= self.a[i * self.nrVM + j + 1]))

            if self.sb_vms_order_by_components_number_order_lex:
                for i in range(0, self.nrComp):
                    l = [self.a[u * self.nrVM + j] == self.a[u * self.nrVM + j + 1] for u in range(0, i)]
                    l.append(sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)]) == sum(
                        [self.a[i + j + 1] for i in range(0, len(self.a), self.nrVM)]))
                    self.solver.add(Implies(And(l), self.a[i * self.nrVM + j] >= self.a[i * self.nrVM + j + 1]))
        # VMs are ordered decreasingly based on price

        if self.sb_lex:
            print("!!!!!sb_lex",self.sb_lex)
            for j in range(max_id + 1, self.nrVM - 1):
                for i in range(0, self.nrComp):
                    l = [self.a[u * self.nrVM + j] == self.a[u * self.nrVM + j + 1] for u in range(0, i)]
                    self.solver.add(Implies(And(l), self.a[i * self.nrVM + j] >= self.a[i * self.nrVM + j + 1]))




            # for j in range(max_id + 1, self.nrVM - 1):
            #     #print(self.PriceProv[j] >= self.PriceProv[j + 1])
            #     self.solver.add(self.PriceProv[j] >= self.PriceProv[j + 1])

            if self.sb_vms_order_by_price_vm_load:
                self.solver.add(self.PriceProv[j] == self.PriceProv[j + 1],
                                sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)]) >= sum(
                                    [self.a[i + j + 1] for i in range(0, len(self.a), self.nrVM)])
                                )
        #
        if self.sb_vms_order_by_components_number or self.sb_vms_order_by_components_number_order_lex:
            for j in range(max_id + 1, self.nrVM - 1):
                self.solver.add(sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)]) >= sum(
                    [self.a[i + j + 1] for i in range(0, len(self.a), self.nrVM)]))
            if self.sb_vms_order_by_components_number_order_lex:
                for i in range(0, self.nrComp):
                    l = [self.a[u*self.nrVM + j] == self.a[u*self.nrVM + j+1] for u in range(0, i)]
                    l.append(sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)]) == sum(
                    [self.a[i + j + 1] for i in range(0, len(self.a), self.nrVM)]))
                    self.solver.add(Implies(And(l), self.a[i*self.nrVM + j] >= self.a[i*self.nrVM + j+1]))
        #redundand constraints
        for j in range(self.nrVM - 1):
            # VMs with same type have the same price
            if self.sb_redundant_price:
                self.solver.add(Implies(self.vmType[j] == self.vmType[j + 1],
                                        self.PriceProv[j] == self.PriceProv[j + 1]))
            # VMs with same type have the same number of procs
            if self.sb_redundant_processor:
                self.solver.add(Implies(self.vmType[j] == self.vmType[j+1],
                                        self.ProcProv[j] == self.ProcProv[j + 1]))
            # VMs with same type have the same amount of memory
            if self.sb_redundant_memory:
                self.solver.add(Implies(self.vmType[j] == self.vmType[j+1],
                                    self.MemProv[j] >= self.MemProv[j + 1]))
            # VMs with same type have the same storage
            if self.sb_redundant_storage:
                self.solver.add(Implies(self.vmType[j] == self.vmType[j+1],
                                    self.StorageProv[j] == self.StorageProv[j + 1]))
            # VMs with the same type should be ordered decreasingly on the number of components
            if self.sb_equal_vms_type_order_by_components_number:
                self.solver.add(Implies(self.vmType[j] == self.vmType[j+1],
                                    sum([self.a[i+j] for i in range(0, len(self.a), self.nrVM)]) >=
                                      sum([self.a[i+j+1] for i in range(0, len(self.a), self.nrVM)])))
            # VMs with the same type should occupy columns from top left
            if self.sb_equal_vms_type_order_lex:
                for i in range(0, self.nrComp):
                    l = [self.a[u*self.nrVM + j] == self.a[u*self.nrVM + j+1] for u in range(0, i)]
                    l.append(self.vmType[j] == self.vmType[j+1])
                    self.solver.add(Implies(And(l), self.a[i*self.nrVM + j] >= self.a[i*self.nrVM + j+1]))
            # One to one dependency
            if self.sb_one_to_one_dependency:
                for one_to_one_group in self.problem.one_to_one_dependencies:
                    component = -1
                    for first_item in one_to_one_group:
                        component=first_item
                        break
                    for comp_id in one_to_one_group:
                        self.solver.add(self.a[comp_id * self.nrVM + component] == 1)

        #lex order on line
        #component 0
        #print("self.sb_lex_line",self.sb_lex_line, self.sb_lex_line_price)
        if self.sb_lex_line:
            print("sb_lex_line", self.sb_lex_line)
            instances_nr = 0
            for vm_id in range(self.nrVM-1):
                self.solver.add(self.a[vm_id] >= self.a[vm_id+1])
            instances_nr = self.problem.componentsList[0].minimumNumberOfInstances
            if self.sb_lex_line_price:
                for vm_id in range(instances_nr-1):
                    self.solver.add(self.PriceProv[vm_id] >= self.PriceProv[vm_id + 1])
                    #print(self.PriceProv[vm_id] >= self.PriceProv[vm_id + 1])

            for comp_id in range(1,self.nrComp):
                for vm_id in range(instances_nr+1, self.nrVM - 1):
                    self.solver.add(self.a[comp_id*self.nrVM + vm_id] >= self.a[comp_id*self.nrVM + vm_id + 1])
                if self.sb_lex_line_price:
                    for vm_id in range(instances_nr + 1, instances_nr+ self.problem.componentsList[comp_id].minimumNumberOfInstances-1):
                        self.solver.add(self.PriceProv[vm_id] >= self.PriceProv[vm_id + 1])
                instances_nr += self.problem.componentsList[comp_id].minimumNumberOfInstances

        if self.sb_lex_col_binary:
            for vm_id in range(self.nrVM - 1):
                list_comps = []
                for comp_id in range(self.nrComp):
                    if not self.problem.componentsList[comp_id].fullDeployedComponent:
                        list_comps.append(comp_id)
            n = len(list_comps)
            n = n - 1
            for vm_id in range(self.nrVM-1):
                self.solver.add(sum([self.a[list_comps[i]*self.nrVM+vm_id]*(2**(n-i)) for i in range(len(list_comps))]) >=
                                sum([self.a[list_comps[i] * self.nrVM+vm_id+1] * (2 ** (n-i)) for i in range(len(list_comps))]))

    def RestrictionPriceOrder(self, start_vm_id, end_vm_id):
        if self.sb_fix_lex and (not self.sb_vms_order_by_price):
            print("ffffffffff")
            print("sb_fix_lex", self.sb_fix_lex)
            for j in range(start_vm_id, end_vm_id - 1):
                for i in range(0, self.nrComp):
                    l = [self.a[u * self.nrVM + j] == self.a[u * self.nrVM + j + 1] for u in range(0, i)]
                    self.solver.add(Implies(And(l), self.a[i * self.nrVM + j] >= self.a[i * self.nrVM + j + 1]))

        if not self.sb_fix_lex:
            if start_vm_id != 0 or end_vm_id!= self.nrVM:
                return

        if self.sb_vms_order_by_price:
            print("here", start_vm_id, end_vm_id - 1)
            for j in range(start_vm_id, end_vm_id-1):
                self.solver.add(self.PriceProv[j] >= self.PriceProv[j + 1])
                if self.sb_lex_price:

                    #for k in range(start_vm_id, end_vm_id - 1):
                        for i in range(0, self.nrComp):
                            l=[self.PriceProv[j] == self.PriceProv[j + 1]]
                            l.extend([self.a[u * self.nrVM + j] == self.a[u * self.nrVM + j + 1] for u in range(0, i)])
                            self.solver.add(Implies(And(l), self.a[i * self.nrVM + j] >= self.a[i * self.nrVM + j + 1]))

    def RestrictionFixComponentOnVM(self, comp_id, vm_id, value):
        """
        Force placing component on a specific VM
        :param comp_id: the ID of the component
        :param vm_id: the ID of the VM
        :return: None
        """
        if not self.sb_fix_variables:
            return
        if value == 1:
            if self.solverTypeOptimize:
                self.solver.add(self.a[comp_id * self.nrVM + vm_id] == 1)
                for compId in self.problem.componentsList[comp_id].conflictComponentsList:
                    self.solver.add(self.a[compId * self.nrVM + vm_id] == 0)

            else:
                self.solver.assert_and_track(self.a[comp_id * self.nrVM + vm_id] == 1, "Label: " + str(self.labelIdx))
                self.labelIdx += 1
        else:
            self.solver.add(self.a[comp_id * self.nrVM + vm_id] == 0)
        # self.__addPriceOffer(comp_id, vm_id)
        self.vm_with_offers[vm_id] = comp_id
        self.vmIds_for_fixedComponents.add(vm_id)

    def _encodeOffers(self, scale_factor):
        #print("scale_factor ", scale_factor)
        # encode offers
        for j in range(self.nrVM):
            self.solver.add(self.PriceProv[j] >= 0)

        if self.use_vm_vector_in_encoding:
            for i in range(self.nrVM):
                if self.solverTypeOptimize:
                    self.solver.add(Implies(self.vm[i] == 0, self.PriceProv[i] == 0))
                else:
                    self.solver.assert_and_track(Implies(self.vm[i] == 0, self.PriceProv[i] == 0), "Label: " + str(self.labelIdx))
                    self.labelIdx += 1
        else:
            for j in range(self.nrVM):
                self.solver.add(Implies(sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)]) == 0, self.PriceProv[j] == 0))

        priceIndex = len(self.offers_list[0]) - 1
        if self.default_offers_encoding:
            for vm_id in range(self.nrVM):
                index = 0
                availableOffers = []
                for offer in self.offers_list:
                    index += 1
                    addOffer = True
                    if self.offers_list_filtered:
                        if vm_id in self.vm_with_offers:
                            # testez daca oferta e aplicabila
                            comp_id = self.vm_with_offers[vm_id]
                            if offer[1] < self.problem.componentsList[comp_id].HC:
                                addOffer = False
                            elif offer[2] < self.problem.componentsList[comp_id].HM:
                                addOffer = False
                            elif offer[3] < self.problem.componentsList[comp_id].HS:
                                addOffer = False
                    if addOffer:
                        availableOffers.append(index)
                        if self.use_vm_vector_in_encoding:
                            if self.solverTypeOptimize:
                                self.solver.add(
                                    Implies(And(self.vm[vm_id] == 1, self.vmType[vm_id] == index),
                                            And(self.PriceProv[vm_id] == (offer[priceIndex] if int(scale_factor) == 1 else offer[priceIndex] / scale_factor),
                                                self.ProcProv[vm_id] == offer[1],
                                                self.MemProv[vm_id] == (offer[2] if int(scale_factor) == 1 else offer[2] / scale_factor),
                                                self.StorageProv[vm_id] == (offer[3] if int(scale_factor) == 1 else offer[3] / scale_factor)
                                                )
                                    ))
                            else:
                                self.solver.assert_and_track(
                                    Implies(And(self.vm[vm_id] == 1, self.vmType[vm_id] == index),
                                            And(self.PriceProv[vm_id] == (offer[priceIndex] if int(scale_factor)==1 else offer[priceIndex]/ scale_factor),
                                                 self.ProcProv[vm_id] == offer[1],
                                                 self.MemProv[vm_id] == (offer[2] if int(scale_factor) ==1 else offer[2] / scale_factor),
                                                 self.StorageProv[vm_id] == (offer[3] if int(scale_factor) ==1 else offer[3] / scale_factor)
                                                )
                                    ), "Label: " + str(self.labelIdx))
                                self.labelIdx += 1
                        else:
                            price = offer[priceIndex] if int(scale_factor) == 1 else offer[priceIndex] / scale_factor
                            self.solver.add(
                                Implies(And(sum([self.a[i + vm_id] for i in range(0, len(self.a), self.nrVM)]) >= 1,
                                            self.vmType[vm_id] == index),
                                        And(self.PriceProv[vm_id] == price,
                                            self.ProcProv[vm_id] == offer[1],
                                            self.MemProv[vm_id] == (offer[2] if int(scale_factor) == 1 else offer[2] / scale_factor),
                                            self.StorageProv[vm_id] == (offer[3] if int(scale_factor) == 1 else offer[3] / scale_factor)
                                            )
                                        ))

                lst = [self.vmType[vm_id] == offerID for offerID in availableOffers]
                self.solver.add(Or(lst))
        else:
            # new encoding
            for vm_id in range(self.nrVM):
                index = 0
                for offer in self.offers_list:
                    index += 1
                    price = offer[priceIndex] if int(scale_factor) == 1 else offer[priceIndex] / scale_factor
                    if self.use_vm_vector_in_encoding:
                        if self.solverTypeOptimize:
                            self.solver.add(
                                Implies(And(self.vm[vm_id] == 1, self.vmType[vm_id] == index),
                                        self.PriceProv[vm_id] == price
                                        ))
                        else:
                            self.solver.assert_and_track(
                                Implies(And(self.vm[vm_id] == 1, self.vmType[vm_id] == index),
                                        self.PriceProv[vm_id] == price, "Label: " + str(self.labelIdx)))
                            self.labelIdx += 1
                    else:
                        self.solver.add(
                            Implies(And(sum([self.a[i + vm_id] for i in range(0, len(self.a), self.nrVM)]) >= 1,
                                        self.vmType[vm_id] == index),
                                    self.PriceProv[vm_id] == price,
                                    ))

    def RestrictionConflict(self, alphaCompId, conflictCompsIdList):
        """
        Constraint describing the conflict between components. The 2 params. should not be placed on the same VM
        :param alphaCompId: id of the first conflict component
        :param conflictCompsIdList: id of the second conflict component
        :return: None
        """
        self.problem.logger.debug(
            "RestrictionConflict: alphaCompId = {} conflictComponentsList = {}".format(alphaCompId,
                                                                                       conflictCompsIdList))
        for j in range(self.nrVM):
            for conflictCompId in conflictCompsIdList:
                # self.problem.logger.debug("...{} <= 1".format([self.a[alphaCompId * self.nrVM + j], self.a[conflictCompId * self.nrVM + j]]))
                if self.solverTypeOptimize:
                    self.solver.add(sum([self.a[alphaCompId * self.nrVM + j],
                                         self.a[conflictCompId * self.nrVM + j]]) <= 1)
                else:
                    self.solver.assert_and_track(
                        sum([self.a[alphaCompId * self.nrVM + j], self.a[conflictCompId * self.nrVM + j]]) <= 1,
                        "LabelConflict: " + str(self.labelIdx_conflict))
                    self.labelIdx_conflict += 1

    def RestrictionOneToOneDependency(self, alphaCompId, betaCompId):
        """
        Contraint describing that alphaCompId and betaCompId should be deployed on the same VM
        :param alphaCompId: id of the first component
        :param betaCompId: id of the second component
        :return: None
        """
        for j in range(self.nrVM):
            if self.solverTypeOptimize:
                self.solver.add(
                    self.a[alphaCompId * self.nrVM + j] == self.a[betaCompId * self.nrVM + j])
            else:
                self.solver.assert_and_track(
                    self.a[alphaCompId * self.nrVM + j] == self.a[betaCompId * self.nrVM + j],
                    "LabelOneToOne" + str(self.labelIdx))
                self.labelIdx_oneToOne += 1

    def RestrictionManyToManyDependency(self, alphaCompId, betaCompId, relation):
        """
        The number of instances of component alphaCompId depends on the number of instances of component betaCompId
        :param alphaCompId: id of the first component
        :param betaCompId: id of the second component
        :param relation: one of the strings in the set {"=", "<=", ">="}
            "=": sum(instances of alpha component) == sum(instances of beta component)
            "<=": sum(instances of alpha component) <= sum(instances of beta component)
            ">=": sum(instances of alpha component) >= sum(instances of beta component)
        :return: None
        """
        if relation == "<=":
            if self.solverTypeOptimize:
                self.solver.add(
                    sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) <=
                    sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]))
            else:
                self.solver.assert_and_track(
                    sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) <=
                    sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]), "LabelManyToMany1: " + str(self.labelIdx))
                self.labelIdx += 1
        elif relation == ">=":
            if self.solverTypeOptimize:
                self.solver.add(
                    sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) >=
                    sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]))
            else:
                self.solver.assert_and_track(
                    sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) >=
                    sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]), "LabelManyToMany2: " + str(self.labelIdx))
                self.labelIdx += 1
        elif relation == "=":
            if self.solverTypeOptimize:
                self.solver.add(
                    sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) ==
                    sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]))
            else:
                self.solver.assert_and_track(
                    sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) ==
                    sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]), "LabelManyToMany3: " + str(self.labelIdx))
                self.labelIdx += 1

    def RestrictionOneToManyDependency(self, alphaCompId, betaCompId, noInstances):
        """
        At each alphaCompId component should be deployed noInstances betaCompId components
        :param alphaCompId: id of the first component
        :param betaCompId: id of the second component
        :param noInstances: depending instances number
        :return: None
        """
        if self.solverTypeOptimize:
            self.solver.add(
                noInstances * sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) -
                              sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]) > 0)
        else:
            self.solver.assert_and_track(
                noInstances * sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) -
                              sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]) > 0, "LabelOneToMany: " + str(self.labelIdx))
            self.labelIdx += 1

        if self.solverTypeOptimize:
            self.solver.add(
                noInstances * sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) -
                              sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]) <= noInstances)
        else:
            self.solver.assert_and_track(
                noInstances * sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) -
                              sum([self.a[betaCompId  * self.nrVM + j] for j in range(self.nrVM)]) <= noInstances, "LabelOneToMany: " + str(self.labelIdx))
            self.labelIdx += 1

    def RestrictionUpperLowerEqualBound(self, compsIdList, bound, operator):
        """
        Defines an upper/lower/equal bound on the number of instances that a component must have
        :param compsIdList: list of components
        :param bound: a positive number
        :param operator: <=, >=, =
            "<=": sum(compsIdList) <= bound
            ">=": sum(compsIdList) >= bound
            "==":  sum(compsIdList) == bound
        :return: None
        """

        self.problem.logger.debug("RestrictionUpperLowerEqualBound: {} {} {} ".format(compsIdList, operator, bound))

        if operator == "<=":
            if self.solverTypeOptimize:
                self.solver.add(
                    sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)])
                    <= bound)
            else:
                #self.__constMap[str("LabelUpperLowerEqualBound" + str(self.labelIdx))] = sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) <= bound
                self.solver.assert_and_track(
                    sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)])
                    <= bound, "LabelUpperLowerEqualBound" + str(self.labelIdx))
                self.labelIdx += 1
        elif operator == ">=":
            if self.solverTypeOptimize:
                self.solver.add(
                    sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) >= bound)
            else:
                #self.__constMap[str("LabelUpperLowerEqualBound" + str(self.labelIdx))] = sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) >= bound
                self.solver.assert_and_track(
                    sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) >= bound, "LabelUpperLowerEqualBound" + str(self.labelIdx))
                self.labelIdx += 1
        elif operator == "=":
            if self.solverTypeOptimize:
                self.solver.add(
                    sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) == bound)
            else:
                #self.__constMap[str("LabelUpperLowerEqualBound" + str(self.labelIdx))] = sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) == bound

                self.solver.assert_and_track(
                    sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) == bound, "LabelUpperLowerEqualBound" + str(self.labelIdx))
                self.labelIdx += 1
        else:
            self.problem.logger.info("Unknown operator")

    def RestrictionRangeBound(self, compsIdList, lowerBound, upperBound):
        """
        Defines a lower and upper bound of instances that a component must have
        :param compsIdList: list of components
        :param lowerBound: a positive number
        :param upperBound: a positive number
        :return:
        """
        for i in range(len(compsIdList)): compsIdList[i] -= 1
        if self.solverTypeOptimize:
            self.solver.add(sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) >= lowerBound)
        else:
            self.solver.assert_and_track(
                sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) >= lowerBound, "LabelRangeBound: " + str(self.labelIdx))
            self.labelIdx += 1
        if self.solverTypeOptimize:
            self.solver.add(sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) <= upperBound)
        else:
            self.solver.assert_and_track(
                sum([self.a[compId * self.nrVM + j] for compId in compsIdList for j in range(self.nrVM)]) <= upperBound, "LabelRangeBound: " + str(self.labelIdx))
            self.labelIdx += 1

    def RestrictionFullDeployment(self, alphaCompId, notInConflictCompsIdList):
        """
        Adds the fact that the component alphaCompId must be deployed on all machines except the ones that contain
         components that alphaCompId alpha is in conflict with
        :param alphaCompId: the component which must be fully deployed
        :param notInConflictCompsIdList: the list of components that alphaCompId is not in conflict in
        :return: None
        """
        for j in range(self.nrVM):
            if self.use_vm_vector_in_encoding:
                if self.solverTypeOptimize:
                    self.solver.add(
                        sum([self.a[alphaCompId * self.nrVM + j]] + [self.a[_compId * self.nrVM + j] for _compId in
                                                                     notInConflictCompsIdList]) == self.vm[j])
                else:
                    self.solver.assert_and_track(
                        sum([self.a[alphaCompId * self.nrVM + j]] + [self.a[_compId * self.nrVM + j] for _compId in
                                                                     notInConflictCompsIdList]) == self.vm[j],
                        "LabelFullDeployment: " + str(self.labelIdx))
                    self.labelIdx += 1
            else:
                if self.solverTypeOptimize:
                    self.solver.add(
                        (sum([self.a[alphaCompId * self.nrVM + j]] + [self.a[_compId * self.nrVM + j] for _compId in
                                                                      notInConflictCompsIdList]))
                        ==
                        (If(sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)]) >= 1, 1, 0)))
                else:
                    self.solver.assert_and_track(
                        (sum([self.a[alphaCompId * self.nrVM + j]] + [self.a[_compId * self.nrVM + j] for _compId in
                                                                      notInConflictCompsIdList]))
                        ==
                        (If(sum([self.a[i + j] for i in range(0, len(self.a), self.nrVM)]) >= 1, 1, 0)),
                        "LabelFullDeployment: " + str(self.labelIdx)
                    )
                    self.labelIdx += 1

    def RestrictionRequireProvideDependency(self, alphaCompId, betaCompId, alphaCompIdInstances, betaCompIdInstances):
        """
        The number of instances of component alpha depends on the number of instances of component beta
        :param alphaCompId: id of the first component
        :param betaCompId: id of the second component
        :param alphaCompIdInstances: number of instances of component alphaCompId
        :param betaCompIdInstances: number of instances of component betaCompId
        :return: None
        """
        # self.problem.logger.debug("RestrictionRequireProvideDependency: alphaCompId={}, betaCompId={}, alphaCompIdInstances={}, "
        #                          "betaCompIdInstances={}".format(alphaCompId, betaCompId, alphaCompIdInstances, betaCompIdInstances))

        if self.solverTypeOptimize:
            self.solver.add(
                alphaCompIdInstances * sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) <=
                betaCompIdInstances * sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]))
        else:
            self.__constMap["LabelRequireProvide: " + str(self.labelIdx)] = \
                alphaCompIdInstances * sum([If(self.a[alphaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]) \
                <= \
                betaCompIdInstances * sum([If(self.a[betaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)])
            self.solver.assert_and_track(
                alphaCompIdInstances * sum([If(self.a[alphaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]) <=
                betaCompIdInstances * sum([If(self.a[betaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]),
                "LabelRequireProvide: " + str(self.labelIdx))
            self.labelIdx += 1
    def RestrictionAlphaOrBeta(self, alphaCompId, betaCompId):
        """
        Describes the fact that alphaCompId or betaCompId not both
        :param alphaCompId: id of the first component
        :param betaCompId: id of the second component
        :return:
        """
        self.problem.logger.debug("RestrictionAlphaOrBeta: alphaCompId={}, betaCompId={}".format(alphaCompId, betaCompId))
        if self.solverTypeOptimize:
            self.solver.add(Or(sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]) == 0,
                               sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]) >= 1))

            self.solver.add(Or(sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) == 0,
                               sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) >= 1))

            self.solver.add(sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]) +
                            sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) >= 1)

            # self.solver.add(
            #     Xor(sum([self.a[betaCompId * self.nrVM + j] for j in range(self.nrVM)]) == 0,
            #         sum([self.a[alphaCompId * self.nrVM + j] for j in range(self.nrVM)]) == 0, True))
        else:
            self.solver.assert_and_track(
                Or(sum([If(self.a[betaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]) == 0,
                   sum([If(self.a[betaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]) >= 1),
                "LabelAlphaOrBeta: " + str(self.labelIdx))
            self.labelIdx += 1

            self.solver.assert_and_track(
                Or(sum([If(self.a[alphaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]) == 0,
                   sum([If(self.a[alphaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]) >= 1),
                "LabelAlphaOrBeta: " + str(self.labelIdx))
            self.labelIdx += 1

            self.solver.assert_and_track(sum([If(self.a[betaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)]) +
                                         sum([If(self.a[alphaCompId * self.nrVM + j], 1, 0) for j in range(self.nrVM)])
                                         >= 1, "LabelAlphaOrBeta: " + str(self.labelIdx))
            self.labelIdx += 1


    def _constraintsHardware(self, componentsRequirements, scale_factor):
        """
        Describes the hardware requirements for each component
        :param componentsRequirements: list of components requirements as given by the user
        :return: None
        """
        self.problem.logger.debug("constraintsHardware: componentsRequirements={}".format(componentsRequirements))
        componentsRequirements = [[0 if i is None else i for i in line] for line in componentsRequirements]

        if self.default_offers_encoding:
            tmp = []
            for k in range(self.nrVM):
                tmp.append(sum([self.a[i * self.nrVM + k] * (componentsRequirements[i][0]) for i in range(self.nrComp)]) <=
                           self.ProcProv[k])
                tmp.append(sum([self.a[i * self.nrVM + k] * ((componentsRequirements[i][1] if int(scale_factor)==1 else componentsRequirements[i][1]/ scale_factor)) for i in range(self.nrComp)]) <=
                           self.MemProv[k])
                tmp.append(sum([self.a[i * self.nrVM + k] * ((componentsRequirements[i][2] if int(scale_factor)==1 else componentsRequirements[i][2]/ scale_factor)) for i in range(self.nrComp)]) <=
                           self.StorageProv[k])
            self.solver.add(tmp)
        else:
            components_Requirements = componentsRequirements.copy()
            if scale_factor != 1:
                for i in range(self.nrComp):
                    components_Requirements[i][1] /= scale_factor
                    components_Requirements[i][2] /= scale_factor
            cpu_values = {}
            memory_values = {}
            storage_values = {}
            index = 0
            for offer in self.offers_list:
                index += 1
                cpu = offer[1]
                if cpu in cpu_values:
                    cpu_values[cpu].append(index)
                else:
                    cpu_values[cpu] = [index]

                memory = offer[2] if scale_factor == 1 else (offer[2] /scale_factor)

                if memory in memory_values:
                    memory_values[memory].append(index)
                else:
                    memory_values[memory] = [index]

                storage = offer[3] if int(scale_factor) == 1 else (offer[3] /scale_factor)
                if storage in storage_values:
                    storage_values[storage].append(index)
                else:
                    storage_values[storage] = [index]

            tmp1 = []
            tmp2 = []
            tmp3 = []
            for k in range(self.nrVM):
                #reversed(sorted(test_dict.keys()))
                #for key, val in cpu_values.items():
                keys = list(cpu_values.keys())
                keys.sort(reverse=True)

                key = keys[0]
                tmp1.append(Implies(
                    sum([self.a[i * self.nrVM + k] * (components_Requirements[i][0]) for i in range(self.nrComp)]) >
                    key, self.vmType[k] == 0)
                )
                offers_aplicable = cpu_values[key].copy()
                keys.pop(0)
                for key in keys:
                    values = cpu_values[key]
                    tmp1.append(Implies(
                        sum([self.a[i * self.nrVM + k] * (components_Requirements[i][0]) for i in range(self.nrComp)]) >
                    key, Or([self.vmType[k] == index for index in offers_aplicable])
                    ))
                    offers_aplicable.extend(values)
                    offers_aplicable.sort()


                key = keys.pop()
                tmp1.append(Implies(
                    sum([self.a[i * self.nrVM + k] * (components_Requirements[i][0]) for i in range(self.nrComp)]) <=
                    key, Or([self.vmType[k] == index for index in offers_aplicable])
                ))

                keys = list(memory_values.keys())
                keys.sort(reverse=True)

                key = keys[0]
                tmp3.append(Implies(
                    sum([self.a[i * self.nrVM + k] * (components_Requirements[i][1]) for i in range(self.nrComp)]) >
                    key, self.vmType[k] == 0)
                )
                offers_aplicable = memory_values[key].copy()
                offers_aplicable.sort()
                keys.pop(0)

                for key in keys:
                    values = memory_values[key]
                    tmp3.append(Implies(
                        sum([self.a[i * self.nrVM + k] * (components_Requirements[i][1]) for i in
                             range(self.nrComp)]) >
                        key, Or([self.vmType[k] == index for index in offers_aplicable])
                    ))
                    offers_aplicable.extend(values)
                    offers_aplicable.sort()

                key = keys.pop()
                tmp2.append(Implies(
                    sum([self.a[i * self.nrVM + k] * (components_Requirements[i][1]) for i in range(self.nrComp)]) <=
                    key, Or([self.vmType[k] == index for index in offers_aplicable])
                ))

                keys = list(storage_values.keys())
                keys.sort(reverse=True)
                key = keys[0]
                tmp2.append(Implies(
                    sum([self.a[i * self.nrVM + k] * (components_Requirements[i][2]) for i in range(self.nrComp)]) >
                    key, self.vmType[k] == 0)
                )

                offers_aplicable = storage_values[key].copy()
                offers_aplicable.sort()
                keys.pop(0)

                for key in keys:
                    values = storage_values[key]

                    tmp2.append(Implies(
                        sum([self.a[i * self.nrVM + k] * (components_Requirements[i][2]) for i in
                             range(self.nrComp)]) >
                        key, Or([self.vmType[k] == index for index in offers_aplicable])
                    ))
                    offers_aplicable.extend(values)
                    offers_aplicable.sort()

                key = keys.pop()
                tmp3.append(Implies(
                    sum([self.a[i * self.nrVM + k] * (components_Requirements[i][2]) for i in
                         range(self.nrComp)]) <=
                    key, Or([self.vmType[k] == index for index in offers_aplicable])
                ))
            self.solver.add(tmp1)
            self.solver.add(tmp2)
            self.solver.add(tmp3)

    def createSMT2LIBFile(self, fileName):
        """
        File creation
        :param fileName: string representing the file name storing the SMT2LIB formulation of the problem
        :return:
        """
        #with open(fileName, 'w+') as fo:
        #   fo.write("(set-logic QF_LIA)\n") # quantifier free linear integer-real arithmetic
        #fo.close()
        if fileName is None: return
        with open(fileName, 'w+') as fo:
            fo.write(self.solver.sexpr())
        fo.close()

    def createSMT2LIBFileSolution(self, fileName, status, model):
        """
        File creation
        :param fileName: string representing the file name storing the SMT2LIB formulation of the problem
        :param status: SAT/UNSAT
        :param model: string representing key-values pairs for the variables in the model
        :return:
        """
        if fileName is None: return
        with open(fileName, 'w+') as foo:
            foo.write(repr(status)+ '[\n')
            for k in model:
                foo.write('%s = %s, ' % (k, model[k]))
                foo.write('\n')
            foo.write(']')
        foo.close()

    def convert_price(self, price):
        return price

    def run(self):
        """
        Invokes the solving of the problem (solution and additional effect like creation of special files)
        :param smt2lib: string indicating a file name storing the SMT2LIB encoding of the problem
        :param smt2libsol: string indicating a file name storing the solution of the problem together with a model (if applicable)
        :return:
        """

        if self.solverTypeOptimize:
            opt = sum(self.PriceProv)
            min = self.solver.minimize(opt)
        self.createSMT2LIBFile(self.smt2lib)

        from datetime import datetime

        now = datetime.now()

        current_time = now.strftime("%H:%M:%S")
        print("Current Time =", current_time)

        startime = time.time()
        status = self.solver.check()
        stoptime = time.time()

        if not self.solverTypeOptimize:
            c = self.solver.unsat_core()
            self.problem.logger.debug("unsat_constraints= {}".format(c))
            print("unsat_constraints= {}".format(c))
            # for cc in c:
            #     self.problem.logger.debug(
            #         "Constraint label: {} constraint description {}".format(str(cc), self.__constMap[cc]))

        self.problem.logger.info("Z3 status: {}".format(status))


        if status == sat:
            model = self.solver.model()
            print("Column represents VM number")
            a_mat = []
            for i in range(self.nrComp):
                l = []
                for k in range(self.nrVM):
                    l.append(model[self.a[i * self.nrVM + k]])
                a_mat.append(l)
                print(l)
            #print("Price for each machine")
            vms_price = []
            for k in range(self.nrVM):
                vms_price.append(model[self.PriceProv[k]])
            #print(vms_price)
            #print("Type for each machine")
            vms_type = []
            for k in range(self.nrVM):
                vms_type.append(model[self.vmType[k]])
            #print(vms_type)
        else:
            print("UNSAT")
        if self.solverTypeOptimize:
            if status == sat:
                #print("a_mat", a_mat)
                self.createSMT2LIBFileSolution(self.smt2libsol, status, model)
                # do not return min.value() since the type is not comparable with -1 in the exposeRE
                return self.convert_price(min.value()), vms_price, stoptime - startime, a_mat, vms_type
            else:
                # unsat
                return -1, None, None, None, None
        else:
            return None, None, stoptime - startime