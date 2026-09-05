; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 2.0) x))
(assert
 (>= 2.0 x))
(assert
 (let ((?x32 (^ x 2.0)))
(and (distinct ?x32 x) true)))
(check-sat)
