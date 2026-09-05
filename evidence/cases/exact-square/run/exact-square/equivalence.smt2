; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 2.0) x))
(assert
 (>= 2.0 x))
(assert
 (let ((?x10 (^ x 2.0)))
(and (distinct ?x10 ?x10) true)))
(check-sat)
