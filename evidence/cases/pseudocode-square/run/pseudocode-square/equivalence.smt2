; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(assert
 (<= (- 2.0) x))
(assert
 (>= 2.0 x))
(assert
 (let ((?x34 (^ (+ x 1.0) 2.0)))
(and (distinct ?x34 ?x34) true)))
(check-sat)
