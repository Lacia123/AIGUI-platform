class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        new_nums = sorted(enumerate(nums),key=lambda x: x[1],reverse=True)

        the_1st_num=0
        the_2nd_num=0

        for i,v in new_nums:
            if target < v:
             continue
            else:
                the_1st_num = i 
                for s,t in reversed(new_nums):
                    if (v+t)==target:
                        the_2nd_num = s
                        break
        
        return [the_1st_num,the_2nd_num]
                        
                    
             